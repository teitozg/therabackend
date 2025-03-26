import pandas as pd
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os
import sys
import decimal
import argparse
import json

load_dotenv()

# MySQL Connection Parameters
db_params = {
    "host": os.getenv('DB_HOST', '127.0.0.1'),  # Connect to local proxy
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'Atenas9democraci.'),
    "database": os.getenv('DB_NAME', 'thera_final_database'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "connect_timeout": 180
}

def log(message):
    print(f"[{datetime.now().isoformat()}] {message}", file=sys.stderr)

def get_db_connection():
    try:
        return pymysql.connect(**db_params)
    except Exception as e:
        log(f"Database connection error: {str(e)}")
        raise

def create_table_if_not_exists(cursor, table_name, df=None):
    """Create table if it doesn't exist with appropriate columns"""
    
    if table_name == 'started_matches':
        cursor.execute("DROP TABLE IF EXISTS started_matches")
        cursor.execute("""
            CREATE TABLE started_matches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ledger_id VARCHAR(255),
                ledger_description TEXT,
                ledger_status VARCHAR(50),
                ledger_ledger_id VARCHAR(255),
                ledger_effective_date DATETIME,
                ledger_posted_at DATETIME,
                ledger_metadata TEXT,
                ledger_amount_USD DECIMAL(20,2),
                ledger_currency_USD VARCHAR(10),
                ledger_amount_EUR DECIMAL(20,2),
                ledger_currency_EUR VARCHAR(10),
                ledger_amount_GBP DECIMAL(20,2),
                ledger_currency_GBP VARCHAR(10),
                ledger_metadata_latestStripeChargeId VARCHAR(255),
                ledger_metadata_payInType VARCHAR(50),
                ledger_metadata_paymentId VARCHAR(255),
                ledger_metadata_paymentMethodId VARCHAR(255),
                ledger_metadata_stripeBalanceTrxId VARCHAR(255),
                ledger_metadata_stripeExchangeRate DECIMAL(20,10),
                ledger_metadata_type VARCHAR(50),
                ledger_effective_at DATETIME,
                stripe_id VARCHAR(255),
                stripe_amount DECIMAL(10,2),
                stripe_amount_refunded DECIMAL(10,2),
                stripe_currency VARCHAR(10),
                stripe_captured BOOLEAN,
                stripe_converted_amount DECIMAL(10,2),
                stripe_converted_amount_refunded DECIMAL(10,2),
                stripe_converted_currency VARCHAR(10),
                stripe_decline_reason TEXT,
                stripe_description TEXT,
                stripe_fee DECIMAL(10,2),
                stripe_is_link BOOLEAN,
                stripe_link_funding VARCHAR(50),
                stripe_mode VARCHAR(50),
                stripe_paymentintent_id VARCHAR(255),
                stripe_payment_source_type VARCHAR(50),
                stripe_created_date_utc DATETIME DEFAULT NULL,
                stripe_refunded_date_utc DATETIME,
                stripe_statement_descriptor TEXT,
                stripe_status VARCHAR(50),
                stripe_seller_message TEXT,
                stripe_taxes_on_fee DECIMAL(10,2),
                stripe_card_id VARCHAR(255),
                stripe_card_name VARCHAR(255),
                stripe_card_brand VARCHAR(50),
                stripe_card_last4 VARCHAR(10),
                stripe_customer_id VARCHAR(255),
                stripe_customer_email VARCHAR(255),
                merge_source VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX(ledger_id),
                INDEX(stripe_id)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == 'succeeded_matches':
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS succeeded_matches (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_ledger VARCHAR(255),
                description_ledger TEXT,
                status_ledger VARCHAR(50),
                ledger_id VARCHAR(255),
                effective_date DATETIME,
                posted_at DATETIME,
                metadata TEXT,
                amount_USD DECIMAL(20,2),
                currency_USD VARCHAR(10),
                metadata_paymentId VARCHAR(255),
                metadata_type VARCHAR(50),
                id_stripe VARCHAR(255),
                created_date_utc DATETIME,
                amount DECIMAL(20,2),
                currency VARCHAR(10),
                paymentintent_id VARCHAR(255),
                status_stripe VARCHAR(50),
                merge_source VARCHAR(20),
                INDEX(id_ledger),
                INDEX(id_stripe)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == 'balance_reconciliation_summary':
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS balance_reconciliation_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ledger_id VARCHAR(255),
                account_name VARCHAR(255),
                currency VARCHAR(10),
                stripe_net_balance DECIMAL(20,2),
                posted_balance DECIMAL(20,2),
                difference DECIMAL(20,2),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return
    
    # Para otras tablas, usar el esquema dinámico basado en DataFrame
    if df is not None:
        columns = []
        for column in df.columns:
            column_clean = column.replace(' ', '_').replace(':', '_').replace('(', '_').replace(')', '_')
            columns.append(f"`{column_clean}` LONGTEXT")
        
        create_statement = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {','.join(columns)}
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """
        cursor.execute(create_statement)

def upload_to_mysql(df, table_name):
    """Upload DataFrame to MySQL table"""
    try:
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor()

        # Drop existing data if table exists
        cursor.execute(f"TRUNCATE TABLE `{table_name}`")
        conn.commit()

        # Convert data types
        df_clean = df.copy()
        
        # Convert all categorical columns to string
        for col in df_clean.select_dtypes(include=['category']).columns:
            df_clean[col] = df_clean[col].astype(str)
        
        # Handle datetime columns
        for col in df_clean.select_dtypes(include=['datetime64']).columns:
            df_clean[col] = df_clean[col].fillna(pd.Timestamp('1900-01-01'))
            df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle numeric columns
        for col in df_clean.select_dtypes(include=['number']).columns:
            df_clean[col] = df_clean[col].fillna(0)
        
        # Convert all remaining columns to string and handle NaN values
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].fillna('')
            df_clean[col] = df_clean[col].astype(str)
            # Replace various null values with empty string
            df_clean[col] = df_clean[col].replace({
                'nan': '', 
                'NaN': '', 
                'None': '', 
                'null': '',
                'NULL': ''
            })

        log(f"Cleaned data shape: {df_clean.shape}")
        
        # Insert data
        if len(df_clean) > 0:
            columns = ', '.join(f'`{col}`' for col in df_clean.columns)
            placeholders = ', '.join(['%s'] * len(df_clean.columns))
            insert_query = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
            
            # Convert DataFrame to list of tuples
            data = [tuple(x) for x in df_clean.values]
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                try:
                    cursor.executemany(insert_query, batch)
                    conn.commit()
                    log(f"Inserted batch of {len(batch)} rows")
                except Exception as e:
                    log(f"Error inserting batch: {str(e)}")
                    raise

        return True, "Data uploaded successfully"

    except Exception as e:
        log(f"Error in upload_to_mysql: {str(e)}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def perform_transaction_reconciliation(cursor):
    """Perform reconciliation between individual Stripe and Ledger transactions"""
    try:
        log("Starting transaction reconciliation...")
        
        # 1. First check - Drop and recreate tables to ensure clean state
        log("1. Dropping existing tables...")
        cursor.execute("DROP TABLE IF EXISTS started_matches")
        cursor.execute("DROP TABLE IF EXISTS succeeded_matches")
        
        # 2. Create tables and verify structure
        log("2. Creating tables...")
        create_table_if_not_exists(cursor, 'started_matches')
        create_table_if_not_exists(cursor, 'succeeded_matches')
        
        # 3. Make sure we commit these changes
        conn = pymysql.connect(**db_params)
        conn.commit()
        
        return True
            
    except Exception as e:
        log(f"Error in transaction reconciliation: {str(e)}")
        return False

def perform_balance_reconciliation():
    """Perform reconciliation between Stripe balance and Ledger balances"""
    try:
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor()
        
        log("Starting balance reconciliation...")
        
        try:
            # Get Stripe balance data
            cursor.execute("""
                SELECT sb.net, sb.currency, sb.balance_transaction_id
                FROM Thera_Stripe_Balance_Changes sb
                WHERE sb.net IS NOT NULL
            """)
            stripe_data = cursor.fetchall()
            stripe_balance = pd.DataFrame(stripe_data, 
                                        columns=['net', 'currency', 'balance_transaction_id'])
            
            # Get Started Ledger transactions
            cursor.execute("""
                SELECT *
                FROM Thera_Ledger_Transactions
                WHERE metadata_type = 'PAY_IN_STARTED'  # Keep this filter
                OR metadata_latestStripeChargeId IS NOT NULL  # But make it OR instead of AND
                OR metadata_paymentId IS NOT NULL  # Include any with payment IDs
            """)
            ledger_started = cursor.fetchall()
            
            # Get Succeeded Ledger transactions
            cursor.execute("""
                SELECT *
                FROM Thera_Ledger_Transactions
                WHERE metadata_type = 'PAY_IN_SUCCEEDED'  # Keep this filter
                OR status = 'SUCCEEDED'  # Include any succeeded transactions
            """)
            ledger_succeeded = cursor.fetchall()
            
            # Get ledger account balances
            cursor.execute("""
                SELECT 
                    ledger_id, 
                    name AS account_name, 
                    currency, 
                    CAST(posted_balance AS FLOAT) as posted_balance
                FROM Thera_Ledger_Accounts
                WHERE posted_balance IS NOT NULL
                  AND name IN ('Stripe Revenue', 'Stripe*', 'Stripe Fees', 'Stripe Payroll Balance')
            """)
            ledger_accounts = pd.DataFrame(cursor.fetchall(), 
                                         columns=['ledger_id', 'account_name', 
                                                'currency', 'posted_balance'])
            
            log(f"Found {len(stripe_balance)} Stripe records")
            log(f"Found {len(ledger_started)} Started Ledger transactions")
            log(f"Found {len(ledger_succeeded)} Succeeded Ledger transactions")
            log(f"Found {len(ledger_accounts)} Ledger accounts")
            
            # Join Stripe balance changes with ledger transactions
            merged = pd.merge(
                stripe_balance,
                ledger_started,
                left_on="balance_transaction_id",
                right_on="metadata_stripeBalanceTrxId",
                how="inner"
            )
            
            # Clean and prepare data
            merged['net'] = pd.to_numeric(merged['net'], errors='coerce')
            merged['currency'] = merged['currency'].str.lower()
            merged = merged.dropna(subset=['net', 'ledger_id', 'currency'])
            
            log(f"Merged data shape: {merged.shape}")
            log(f"Sample merged data:\n{merged.head().to_string()}")
            
            # Sum net balance by ledger_id and currency
            stripe_grouped = merged.groupby(['ledger_id', 'currency']).agg(
                stripe_net_balance=pd.NamedAgg(column='net', aggfunc='sum')
            ).reset_index()
            
            log(f"Grouped data shape: {stripe_grouped.shape}")
            log(f"Sample grouped data:\n{stripe_grouped.head().to_string()}")
            
            # Merge with ledger account balances
            reconciliation = pd.merge(
                ledger_accounts,
                stripe_grouped,
                on=['ledger_id', 'currency'],
                how='left'
            )
            
            # Fill NaN values with 0
            reconciliation['stripe_net_balance'] = reconciliation['stripe_net_balance'].fillna(0.0)
            
            # Calculate difference and status
            reconciliation['difference'] = reconciliation['stripe_net_balance'] - reconciliation['posted_balance']
            reconciliation['status'] = reconciliation['difference'].apply(
                lambda x: 'match' if abs(x) < 0.01 else 'mismatch')
            reconciliation['created_at'] = pd.Timestamp.now()
            
            log(f"Final reconciliation shape: {reconciliation.shape}")
            log(f"Sample results:\n{reconciliation.head().to_string()}")
            
            # Upload to database
            cursor.execute("TRUNCATE TABLE balance_reconciliation_summary")
            
            if not reconciliation.empty:
                columns = ', '.join(f'`{col}`' for col in reconciliation.columns)
                placeholders = ', '.join(['%s'] * len(reconciliation.columns))
                insert_query = f"""
                    INSERT INTO balance_reconciliation_summary 
                    ({columns}) VALUES ({placeholders})
                """
                values = [tuple(x) for x in reconciliation.values]
                cursor.executemany(insert_query, values)
                conn.commit()
            
            return True, "Balance reconciliation completed successfully"
            
        except Exception as e:
            log(f"Error during balance reconciliation steps: {str(e)}")
            raise
            
    except Exception as e:
        log(f"Error in balance reconciliation: {str(e)}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def create_tables_if_not_exist(cursor):
    """Create the necessary tables if they don't exist"""
    try:
        # Create started matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_ledger_started_matches (
                balance_transaction_id VARCHAR(255),
                net DECIMAL(10,2),
                currency VARCHAR(10),
                created DATETIME,
                metadata_stripeBalanceTrxId VARCHAR(255),
                ledger_id VARCHAR(255),
                metadata_type VARCHAR(50),
                status VARCHAR(50),
                match_type VARCHAR(20),
                PRIMARY KEY (balance_transaction_id)
            )
        """)
        
        # Create succeeded matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stripe_ledger_succeeded_matches (
                balance_transaction_id VARCHAR(255),
                net DECIMAL(10,2),
                currency VARCHAR(10),
                created DATETIME,
                metadata_stripeBalanceTrxId VARCHAR(255),
                ledger_id VARCHAR(255),
                metadata_type VARCHAR(50),
                status VARCHAR(50),
                match_type VARCHAR(20),
                PRIMARY KEY (balance_transaction_id)
            )
        """)
        
    except Exception as e:
        log(f"Error creating tables: {str(e)}")
        raise

def perform_transaction_matching():
    """Perform transaction matching between Stripe and Ledger"""
    try:
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Create tables if they don't exist
        create_tables_if_not_exist(cursor)
        
        # Get Stripe transactions
        cursor.execute("""
            SELECT balance_transaction_id, net, currency, created
            FROM Thera_Stripe_Balance_Changes
            WHERE net IS NOT NULL
        """)
        stripe_transactions = pd.DataFrame(cursor.fetchall())
        
        # Get Ledger transactions
        cursor.execute("""
            SELECT metadata_stripeBalanceTrxId, ledger_id, metadata_type, status
            FROM Thera_Ledger_Transactions
            WHERE metadata_stripeBalanceTrxId IS NOT NULL
        """)
        ledger_transactions = pd.DataFrame(cursor.fetchall())
        
        # Create matches
        started_matches = pd.merge(
            stripe_transactions,
            ledger_transactions[ledger_transactions['metadata_type'] == 'PAY_IN_STARTED'],
            left_on='balance_transaction_id',
            right_on='metadata_stripeBalanceTrxId',
            how='left'
        )
        
        succeeded_matches = pd.merge(
            stripe_transactions,
            ledger_transactions[ledger_transactions['metadata_type'] == 'PAY_IN_SUCCEEDED'],
            left_on='balance_transaction_id',
            right_on='metadata_stripeBalanceTrxId',
            how='left'
        )
        
        # Prepare started matches
        started_matches['match_type'] = 'stripe_only'
        started_matches.loc[started_matches['metadata_stripeBalanceTrxId'].notna(), 'match_type'] = 'match'
        
        # Prepare succeeded matches
        succeeded_matches['match_type'] = 'stripe_only'
        succeeded_matches.loc[succeeded_matches['metadata_stripeBalanceTrxId'].notna(), 'match_type'] = 'match'
        
        # Upload started matches
        cursor.execute("TRUNCATE TABLE stripe_ledger_started_matches")
        if not started_matches.empty:
            columns = ['balance_transaction_id', 'net', 'currency', 'created', 
                      'metadata_stripeBalanceTrxId', 'ledger_id', 'metadata_type', 
                      'status', 'match_type']
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"""
                INSERT INTO stripe_ledger_started_matches 
                ({', '.join(columns)}) VALUES ({placeholders})
            """
            values = started_matches[columns].fillna('').values.tolist()
            cursor.executemany(insert_query, values)
            conn.commit()
        
        # Upload succeeded matches
        cursor.execute("TRUNCATE TABLE stripe_ledger_succeeded_matches")
        if not succeeded_matches.empty:
            columns = ['balance_transaction_id', 'net', 'currency', 'created', 
                      'metadata_stripeBalanceTrxId', 'ledger_id', 'metadata_type', 
                      'status', 'match_type']
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"""
                INSERT INTO stripe_ledger_succeeded_matches 
                ({', '.join(columns)}) VALUES ({placeholders})
            """
            values = succeeded_matches[columns].fillna('').values.tolist()
            cursor.executemany(insert_query, values)
            conn.commit()
        
        # Convert numpy int64 to regular integers for JSON serialization
        started_stats = {k: int(v) for k, v in started_matches['match_type'].value_counts().items()}
        succeeded_stats = {k: int(v) for k, v in succeeded_matches['match_type'].value_counts().items()}
        
        log(f"Started matches: {started_stats}")
        log(f"Succeeded matches: {succeeded_stats}")
        
        return True, {
            'started_matches': started_stats,
            'succeeded_matches': succeeded_stats
        }
        
    except Exception as e:
        log(f"Error in transaction matching: {str(e)}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def perform_reconciliation():
    """Perform reconciliation between Stripe and Ledger data"""
    try:
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        log("Starting reconciliation process...")
        
        # First drop and recreate tables
        log("Dropping and recreating tables...")
        cursor.execute("DROP TABLE IF EXISTS started_matches")
        cursor.execute("DROP TABLE IF EXISTS succeeded_matches")
        conn.commit()  # Commit the drops
        
        create_table_if_not_exists(cursor, 'started_matches')
        create_table_if_not_exists(cursor, 'succeeded_matches')
        conn.commit()  # Commit the table creation
        
        # Get Stripe transactions
        log("Fetching Stripe transactions...")
        cursor.execute("""
            SELECT 
                id,
                amount,
                amount_refunded,
                currency,
                captured,
                converted_amount,
                converted_amount_refunded,
                converted_currency,
                decline_reason,
                description,
                fee,
                is_link,
                link_funding,
                mode,
                paymentintent_id as PaymentIntent_ID,
                payment_source_type,
                created_date_utc,
                refunded_date_utc,
                statement_descriptor,
                status,
                seller_message,
                taxes_on_fee,
                card_id,
                card_name,
                card_brand,
                card_last4,
                customer_id as Customer_ID,
                customer_email as Customer_Email
            FROM Thera_Stripe_Incoming_Transactions
            WHERE status = 'Paid'
        """)
        stripe_transactions = cursor.fetchall()
        log(f"Found {len(stripe_transactions)} Stripe transactions")
        
        # Get Started Ledger transactions
        log("Fetching Started Ledger transactions...")
        cursor.execute("""
            SELECT *
            FROM Thera_Ledger_Transactions
            WHERE metadata_type = 'PAY_IN_STARTED'  # Keep this filter
            OR metadata_latestStripeChargeId IS NOT NULL  # But make it OR instead of AND
            OR metadata_paymentId IS NOT NULL  # Include any with payment IDs
        """)
        ledger_started = cursor.fetchall()
        log(f"Found {len(ledger_started)} Started Ledger transactions")
        
        # Get Succeeded Ledger transactions
        log("Fetching Succeeded Ledger transactions...")
        cursor.execute("""
            SELECT *
            FROM Thera_Ledger_Transactions
            WHERE metadata_type = 'PAY_IN_SUCCEEDED'  # Keep this filter
            OR status = 'SUCCEEDED'  # Include any succeeded transactions
        """)
        ledger_succeeded = cursor.fetchall()
        log(f"Found {len(ledger_succeeded)} Succeeded Ledger transactions")
        
        # Initialize counters
        started_matches = {'match': 0, 'stripe_only': 0, 'ledger_only': 0}
        started_data = []
        
        # Perform started matches reconciliation
        log("Performing started matches reconciliation...")
        for stripe_tx in stripe_transactions:
            matching_ledger = next(
                (lt for lt in ledger_started 
                 if lt['metadata_latestStripeChargeId'] == stripe_tx['id']),
                None
            )
            
            if matching_ledger:
                merge_source = 'match'
                started_matches['match'] += 1
            else:
                merge_source = 'stripe_only'
                started_matches['stripe_only'] += 1
            
            started_data.append((
                matching_ledger['id'] if matching_ledger else None,
                matching_ledger['description'] if matching_ledger else None,
                matching_ledger['status'] if matching_ledger else None,
                matching_ledger['ledger_id'] if matching_ledger else None,
                matching_ledger['effective_date'] if matching_ledger else None,
                matching_ledger['posted_at'] if matching_ledger else None,
                matching_ledger['metadata'] if matching_ledger else None,
                float(matching_ledger['amount_USD']) if matching_ledger and matching_ledger['amount_USD'] else None,
                matching_ledger['currency_USD'] if matching_ledger else None,
                float(matching_ledger['amount_EUR']) if matching_ledger and matching_ledger['amount_EUR'] else None,
                matching_ledger['currency_EUR'] if matching_ledger else None,
                float(matching_ledger['amount_GBP']) if matching_ledger and matching_ledger['amount_GBP'] else None,
                matching_ledger['currency_GBP'] if matching_ledger else None,
                matching_ledger['metadata_latestStripeChargeId'] if matching_ledger else None,
                matching_ledger['metadata_payInType'] if matching_ledger else None,
                matching_ledger['metadata_paymentId'] if matching_ledger else None,
                matching_ledger['metadata_paymentMethodId'] if matching_ledger else None,
                matching_ledger['metadata_stripeBalanceTrxId'] if matching_ledger else None,
                float(matching_ledger['metadata_stripeExchangeRate']) if matching_ledger and matching_ledger['metadata_stripeExchangeRate'] else None,
                matching_ledger['metadata_type'] if matching_ledger else None,
                matching_ledger['effective_at'] if matching_ledger else None,
                stripe_tx['id'],
                float(stripe_tx['amount']),
                float(stripe_tx['amount_refunded']) if stripe_tx['amount_refunded'] else None,
                stripe_tx['currency'],
                1 if stripe_tx['captured'] else 0,
                float(stripe_tx['converted_amount']) if 'converted_amount' in stripe_tx else None,
                float(stripe_tx['converted_amount_refunded']) if 'converted_amount_refunded' in stripe_tx else None,
                stripe_tx['converted_currency'] if 'converted_currency' in stripe_tx else None,
                stripe_tx['decline_reason'] if 'decline_reason' in stripe_tx else None,
                stripe_tx['description'],
                float(stripe_tx['fee']) if stripe_tx['fee'] else None,
                1 if stripe_tx['is_link'] else 0 if 'is_link' in stripe_tx else None,
                stripe_tx['link_funding'] if 'link_funding' in stripe_tx else None,
                stripe_tx['mode'] if 'mode' in stripe_tx else None,
                stripe_tx['PaymentIntent_ID'],
                stripe_tx['payment_source_type'] if 'payment_source_type' in stripe_tx else None,
                stripe_tx['created_date_utc'],
                stripe_tx['refunded_date_utc'] if 'refunded_date_utc' in stripe_tx else None,
                stripe_tx['statement_descriptor'] if 'statement_descriptor' in stripe_tx else None,
                stripe_tx['status'],
                stripe_tx['seller_message'] if 'seller_message' in stripe_tx else None,
                float(stripe_tx['taxes_on_fee']) if 'taxes_on_fee' in stripe_tx and stripe_tx['taxes_on_fee'] else None,
                stripe_tx['card_id'] if 'card_id' in stripe_tx else None,
                stripe_tx['card_name'] if 'card_name' in stripe_tx else None,
                stripe_tx['card_brand'] if 'card_brand' in stripe_tx else None,
                stripe_tx['card_last4'] if 'card_last4' in stripe_tx else None,
                stripe_tx['Customer_ID'],
                stripe_tx['Customer_Email'],
                merge_source
            ))
        
        # Fix the ledger_only records to provide all required NULL values
        for ledger_tx in ledger_started:
            if not any(sd[0] == ledger_tx['id'] for sd in started_data):
                started_matches['ledger_only'] += 1
                started_data.append((
                    ledger_tx['id'],
                    ledger_tx['description'],
                    ledger_tx['status'],
                    ledger_tx['ledger_id'],
                    ledger_tx['effective_date'],
                    ledger_tx['posted_at'],
                    ledger_tx['metadata'],
                    float(ledger_tx['amount_USD']) if ledger_tx['amount_USD'] else None,
                    ledger_tx['currency_USD'],
                    float(ledger_tx['amount_EUR']) if ledger_tx['amount_EUR'] else None,
                    ledger_tx['currency_EUR'],
                    float(ledger_tx['amount_GBP']) if ledger_tx['amount_GBP'] else None,
                    ledger_tx['currency_GBP'],
                    ledger_tx['metadata_latestStripeChargeId'],
                    ledger_tx['metadata_payInType'],
                    ledger_tx['metadata_paymentId'],
                    ledger_tx['metadata_paymentMethodId'],
                    ledger_tx['metadata_stripeBalanceTrxId'],
                    float(ledger_tx['metadata_stripeExchangeRate']) if ledger_tx['metadata_stripeExchangeRate'] else None,
                    ledger_tx['metadata_type'],
                    ledger_tx['effective_at'],
                    None,  # stripe_id
                    None,  # stripe_amount
                    None,  # stripe_amount_refunded
                    None,  # stripe_currency
                    None,  # stripe_captured
                    None,  # stripe_converted_amount
                    None,  # stripe_converted_amount_refunded
                    None,  # stripe_converted_currency
                    None,  # stripe_decline_reason
                    None,  # stripe_description
                    None,  # stripe_fee
                    None,  # stripe_is_link
                    None,  # stripe_link_funding
                    None,  # stripe_mode
                    None,  # stripe_paymentintent_id
                    None,  # stripe_payment_source_type
                    None,  # stripe_created_date_utc
                    None,  # stripe_refunded_date_utc
                    None,  # stripe_statement_descriptor
                    None,  # stripe_status
                    None,  # stripe_seller_message
                    None,  # stripe_taxes_on_fee
                    None,  # stripe_card_id
                    None,  # stripe_card_name
                    None,  # stripe_card_brand
                    None,  # stripe_card_last4
                    None,  # stripe_customer_id
                    None,  # stripe_customer_email
                    'ledger_only'  # merge_source
                ))
        
        # Insert started matches
        log("Saving started matches...")
        columns = """
            ledger_id, ledger_description, ledger_status, ledger_ledger_id,
            ledger_effective_date, ledger_posted_at, ledger_metadata,
            ledger_amount_USD, ledger_currency_USD, ledger_amount_EUR, ledger_currency_EUR,
            ledger_amount_GBP, ledger_currency_GBP, ledger_metadata_latestStripeChargeId,
            ledger_metadata_payInType, ledger_metadata_paymentId, ledger_metadata_paymentMethodId,
            ledger_metadata_stripeBalanceTrxId, ledger_metadata_stripeExchangeRate,
            ledger_metadata_type, ledger_effective_at, stripe_id, stripe_amount,
            stripe_amount_refunded, stripe_currency, stripe_captured, stripe_converted_amount,
            stripe_converted_amount_refunded, stripe_converted_currency, stripe_decline_reason,
            stripe_description, stripe_fee, stripe_is_link, stripe_link_funding, stripe_mode,
            stripe_paymentintent_id, stripe_payment_source_type, stripe_created_date_utc,
            stripe_refunded_date_utc, stripe_statement_descriptor, stripe_status,
            stripe_seller_message, stripe_taxes_on_fee, stripe_card_id, stripe_card_name,
            stripe_card_brand, stripe_card_last4, stripe_customer_id, stripe_customer_email,
            merge_source
        """
        placeholders = ', '.join(['%s'] * 50)  # Changed from 33 to 50 to match the number of columns
        cursor.executemany(f"""
            INSERT INTO started_matches ({columns})
            VALUES ({placeholders})
        """, started_data)
        
        # Perform succeeded matches reconciliation
        log("Performing succeeded matches reconciliation...")
        succeeded_matches = {'match': 0, 'stripe_only': 0, 'ledger_only': 0}
        succeeded_data = []
        
        for stripe_tx in stripe_transactions:
            matching_ledger = next(
                (lt for lt in ledger_succeeded 
                 if lt['metadata_paymentId'] == stripe_tx['PaymentIntent_ID']),
                None
            )
            
            if matching_ledger:
                merge_source = 'match'
                succeeded_matches['match'] += 1
            else:
                merge_source = 'stripe_only'
                succeeded_matches['stripe_only'] += 1
            
            succeeded_data.append((
                matching_ledger['id'] if matching_ledger else None,
                matching_ledger['description'] if matching_ledger else None,
                matching_ledger['status'] if matching_ledger else None,
                matching_ledger['ledger_id'] if matching_ledger else None,
                matching_ledger['effective_date'] if matching_ledger else None,
                matching_ledger['posted_at'] if matching_ledger else None,
                matching_ledger['metadata'] if matching_ledger else None,
                float(matching_ledger['amount_USD']) if matching_ledger and matching_ledger['amount_USD'] else None,
                matching_ledger['currency_USD'] if matching_ledger else None,
                matching_ledger['metadata_paymentId'] if matching_ledger else None,
                matching_ledger['metadata_type'] if matching_ledger else None,
                stripe_tx['id'],
                stripe_tx['created_date_utc'],
                float(stripe_tx['amount']),
                stripe_tx['currency'],
                stripe_tx['PaymentIntent_ID'],
                stripe_tx['status'],
                merge_source
            ))
        
        # Add ledger_only records for succeeded matches
        for ledger_tx in ledger_succeeded:
            if not any(sd[0] == ledger_tx['id'] for sd in succeeded_data):
                succeeded_matches['ledger_only'] += 1
                succeeded_data.append((
                    ledger_tx['id'],
                    ledger_tx['description'],
                    ledger_tx['status'],
                    ledger_tx['ledger_id'],
                    ledger_tx['effective_date'],
                    ledger_tx['posted_at'],
                    ledger_tx['metadata'],
                    float(ledger_tx['amount_USD']) if ledger_tx['amount_USD'] else None,
                    ledger_tx['currency_USD'],
                    ledger_tx['metadata_paymentId'] if ledger_tx['metadata_paymentId'] else None,
                    ledger_tx['metadata_type'] if ledger_tx['metadata_type'] else None,
                    None, None, None, None, None, None, None, None, None, None, None,
                    'ledger_only'
                ))
        
        # Insert succeeded matches
        log("Saving succeeded matches...")
        succeeded_columns = """
            id_ledger, description_ledger, status_ledger, ledger_id,
            effective_date, posted_at, metadata,
            amount_USD, currency_USD, metadata_paymentId,
            metadata_type, id_stripe, created_date_utc,
            amount, currency, paymentintent_id,
            status_stripe, merge_source
        """
        placeholders = ', '.join(['%s'] * 18)  # Changed from 16 to 18 to match the number of columns
        cursor.executemany(f"""
            INSERT INTO succeeded_matches ({succeeded_columns})
            VALUES ({placeholders})
        """, succeeded_data)
        
        conn.commit()
        log("Reconciliation completed successfully")
        
        return True, {
            'started_matches': started_matches,
            'succeeded_matches': succeeded_matches
        }
        
    except Exception as e:
        log(f"Error during reconciliation: {str(e)}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_summary():
    # Implement the logic to generate a summary based on the reconciled data
    # This is a placeholder and should be replaced with the actual implementation
    return "Summary not implemented"

def get_matches(match_type='started', filters=None):
    """Get matches with optional filtering"""
    try:
        log(f"Starting get_matches with type: {match_type} and filters: {filters}")
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        table_name = 'started_matches' if match_type == 'started' else 'succeeded_matches'
        log(f"Using table: {table_name}")
        
        # First check if table exists
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if not cursor.fetchone():
            log(f"Table {table_name} does not exist")
            return False, f"Table {table_name} does not exist"
        
        # Build query with filters
        query = f"""
            SELECT 
                id_ledger as 'Ledger ID',
                description_ledger as 'Description',
                status_ledger as 'Ledger Status',
                effective_date as 'Date',
                amount_USD as 'Amount USD',
                currency_USD as 'Currency',
                metadata_type as 'Type',
                id_stripe as 'Stripe ID',
                status_stripe as 'Stripe Status',
                merge_source as 'Match Status'
            FROM {table_name}
            WHERE 1=1
        """
        
        params = []
        
        if filters:
            if filters.get('date_from'):
                query += " AND DATE(effective_date) >= %s"
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                query += " AND DATE(effective_date) <= %s"
                params.append(filters['date_to'])
        
        # Add ordering and limit
        query += " ORDER BY effective_date DESC LIMIT 5000"
        
        log(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        log(f"Found {len(results)} matches")
        
        # Convert to list of dicts for JSON serialization
        matches = []
        for row in results:
            match_dict = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    match_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, decimal.Decimal):
                    match_dict[key] = float(value)
                elif value is None:
                    match_dict[key] = ''
                else:
                    match_dict[key] = str(value)
            matches.append(match_dict)
        
        return True, {
            'matches': matches,
            'count': len(matches)
        }
        
    except Exception as e:
        log(f"Error getting matches: {str(e)}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconcile", action="store_true", help="Perform reconciliation")
    parser.add_argument("--get-matches", action="store_true", help="Get matches")
    parser.add_argument("--match-type", choices=["started", "succeeded"], help="Type of matches to get")
    parser.add_argument("--filters", help="JSON string of filters")
    
    args = parser.parse_args()
    log(f"Arguments received: {args}")
    
    if args.reconcile:
        log("Starting reconciliation process...")
        try:
            success, result = perform_reconciliation()
            if not success:
                log(f"Reconciliation failed: {result}")
                sys.exit(1)
            
            # Log statistics to stderr
            log(f"Started matches: {result['started_matches']}")
            log(f"Succeeded matches: {result['succeeded_matches']}")
            
            # Print only the JSON result to stdout
            print(json.dumps(result))  # This will be the only line on stdout
            
        except Exception as e:
            log(f"Error processing reconciliation request: {str(e)}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            sys.exit(1)
        
    elif args.get_matches:
        log("Getting matches...")
        try:
            filters = json.loads(args.filters) if args.filters else None
            log(f"Parsed filters: {filters}")
            success, result = get_matches(args.match_type, filters)
            if not success:
                log(f"Failed to get matches: {result}")
                sys.exit(1)
            log("Successfully got matches, printing result...")
            print(json.dumps(result))
        except Exception as e:
            log(f"Error processing matches request: {str(e)}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            sys.exit(1) 