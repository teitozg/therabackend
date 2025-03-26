import pandas as pd
import pymysql
from datetime import datetime
import argparse
import sys
import os
import json
from reconciliation_service import perform_reconciliation as service_reconciliation
import time
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# MySQL Connection Parameters
db_params = {
    "host": os.getenv('DB_HOST', '127.0.0.1'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'Atenas9democraci.'),
    "database": os.getenv('DB_NAME', 'thera_final_database'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "connect_timeout": 180,
    "read_timeout": 180,
    "write_timeout": 180
}

# Add logging
def log(message):
    print(f"[LOG] {message}", file=sys.stderr)

# Add these column mappings at the top of the file
EXPECTED_COLUMNS = {
    "Thera_Stripe_Balance_Changes": [
        "created",
        "available_on",
        "gross",
        "currency",
        "description",
        "fee",
        "net",
        "balance_transaction_id"
    ],
    "Thera_Stripe_Incoming_Transactions": [
        "created_date_utc",
        "paymentintent_id",
        "id",
        "amount",
        "currency",
        "status"
    ],
    "Thera_Ledger_Transactions": [
        "effective_date", 
        "metadata_type",
        "metadata_latestStripeChargeId",
        "metadata_paymentId"
    ],
    "Thera_Ledger_Accounts": [
        "id",
        "name",
        "currency",
        "posted_balance",
        "ledger_id",
        "metadata_type"
    ]
}

def clean_column_names(columns):
    """Clean column names to match database schema"""
    # Special mapping for metadata fields to preserve casing
    metadata_mapping = {
        'metadata:latestStripeChargeId': 'metadata_latestStripeChargeId',
        'metadata:payInType': 'metadata_payInType',
        'metadata:paymentId': 'metadata_paymentId',
        'metadata:paymentMethodId': 'metadata_paymentMethodId',
        'metadata:stripeBalanceTrxId': 'metadata_stripeBalanceTrxId',
        'metadata:stripeExchangeRate': 'metadata_stripeExchangeRate',
        'metadata:type': 'metadata_type'
    }
    
    # Regular column mappings
    standard_mapping = {
        'Created date (UTC)': 'created_date_utc',
        'PaymentIntent ID': 'paymentintent_id',
        'Amount': 'amount',
        'Currency': 'currency',
        'Status': 'status',
        'id': 'id',
        'payment_metadata[type]': 'payment_metadata_type',
        'created': 'created',
        'available_on': 'available_on',
        'gross': 'gross',
        'currency': 'currency',
        'description': 'description',
        'fee': 'fee',
        'net': 'net',
        'balance_transaction_id': 'balance_transaction_id'
    }
    
    cleaned = []
    for col in columns:
        if col in metadata_mapping:
            cleaned.append(metadata_mapping[col])
        elif col in standard_mapping:
            cleaned.append(standard_mapping[col])
        else:
            # Handle currency-specific amount columns (e.g., amount.USD, amount.EUR)
            if '.' in col:
                prefix, currency = col.split('.')
                cleaned_col = f"{prefix}_{currency.lower()}"
            # Handle metadata fields
            elif col.startswith('metadata:'):
                cleaned_col = col.replace(':', '_')
            # Handle all other columns
            else:
                cleaned_col = (col.lower()
                             .replace(' ', '_')
                             .replace('(', '')
                             .replace(')', '')
                             .replace(':', '_')
                             .replace('[', '_')
                             .replace(']', ''))
            cleaned.append(cleaned_col)
    return cleaned

def validate_columns(df, source_type):
    """Validate that the CSV has the required columns"""
    expected = EXPECTED_COLUMNS.get(source_type, [])
    if not expected:
        raise ValueError(f"Unknown source type: {source_type}")
    
    # Special handling for Stripe Balance Changes
    if source_type == "Thera_Stripe_Balance_Changes":
        # No necesitamos validar las columnas originales
        # porque el archivo ya tiene las columnas correctas
        return True
    
    # Para otros tipos de archivos, continuar con la validación normal
    expected = [col.lower() for col in expected]
    df_columns_lower = {col.lower(): col for col in df.columns}
    
    missing = []
    for expected_col in expected:
        if expected_col not in df_columns_lower:
            missing.append(expected_col)
    
    if missing:
        raise ValueError(f"Missing required columns for {source_type}: {', '.join(missing)}")
    
    return True

def create_table_if_not_exists(cursor, table_name, df=None):
    """Create table if it doesn't exist with appropriate columns"""
    
    if table_name == "Thera_Stripe_Balance_Changes":
        # Primero eliminar la tabla si existe
        cursor.execute("DROP TABLE IF EXISTS Thera_Stripe_Balance_Changes")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Thera_Stripe_Balance_Changes (
                account_id VARCHAR(255),
                account_name VARCHAR(255),
                balance_transaction_id VARCHAR(255) PRIMARY KEY,
                created_utc DATETIME,
                created DATETIME,
                available_on_utc DATETIME,
                available_on DATETIME,
                currency VARCHAR(20),
                gross DECIMAL(20,2),
                fee DECIMAL(20,2),
                net DECIMAL(20,2),
                reporting_category VARCHAR(100),
                source_id VARCHAR(255),
                description TEXT,
                customer_facing_amount DECIMAL(20,2),
                customer_facing_currency VARCHAR(20),
                trace_id VARCHAR(255),
                trace_id_status VARCHAR(50),
                automatic_payout_id VARCHAR(255),
                automatic_payout_effective_at_utc DATETIME,
                automatic_payout_effective_at DATETIME,
                customer_id VARCHAR(255),
                customer_email VARCHAR(255),
                customer_name VARCHAR(255),
                customer_description TEXT,
                customer_shipping_address_line1 TEXT,
                customer_shipping_address_line2 TEXT,
                customer_shipping_address_city VARCHAR(255),
                customer_shipping_address_state VARCHAR(255),
                customer_shipping_address_postal_code VARCHAR(50),
                customer_shipping_address_country VARCHAR(50),
                customer_address_line1 TEXT,
                customer_address_line2 TEXT,
                customer_address_city VARCHAR(255),
                customer_address_state VARCHAR(255),
                customer_address_postal_code VARCHAR(50),
                customer_address_country VARCHAR(50),
                shipping_address_line1 TEXT,
                shipping_address_line2 TEXT,
                shipping_address_city VARCHAR(255),
                shipping_address_state VARCHAR(255),
                shipping_address_postal_code VARCHAR(50),
                shipping_address_country VARCHAR(50),
                card_address_line1 TEXT,
                card_address_line2 TEXT,
                card_address_city VARCHAR(255),
                card_address_state VARCHAR(255),
                card_address_postal_code VARCHAR(50),
                card_address_country VARCHAR(50),
                charge_id VARCHAR(255),
                payment_intent_id VARCHAR(255),
                charge_created_utc DATETIME,
                charge_created DATETIME,
                invoice_id VARCHAR(255),
                invoice_number VARCHAR(255),
                subscription_id VARCHAR(255),
                payment_method_type VARCHAR(100),
                is_link VARCHAR(10),
                card_brand VARCHAR(50),
                card_funding VARCHAR(50),
                card_country VARCHAR(50),
                statement_descriptor TEXT,
                dispute_reason VARCHAR(255),
                payment_metadata_type VARCHAR(100),
                connected_account_id VARCHAR(255),
                connected_account_name VARCHAR(255),
                connected_account_country VARCHAR(50),
                connected_account_direct_charge_id VARCHAR(255)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == "Thera_Stripe_Incoming_Transactions":
        # Primero eliminar la tabla si existe
        cursor.execute("DROP TABLE IF EXISTS Thera_Stripe_Incoming_Transactions")
        
        # Crear la tabla con todas las columnas del CSV
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Thera_Stripe_Incoming_Transactions (
                id VARCHAR(255) PRIMARY KEY,
                created_date_utc DATETIME,
                amount DECIMAL(20,2),
                amount_refunded DECIMAL(20,2),
                currency VARCHAR(20),
                captured VARCHAR(20),
                converted_amount DECIMAL(20,2),
                converted_amount_refunded DECIMAL(20,2),
                converted_currency VARCHAR(20),
                decline_reason TEXT,
                description TEXT,
                fee DECIMAL(20,2),
                is_link VARCHAR(20),
                link_funding VARCHAR(100),
                mode VARCHAR(50),
                paymentintent_id VARCHAR(255),
                payment_source_type VARCHAR(100),
                refunded_date_utc DATETIME,
                statement_descriptor TEXT,
                status VARCHAR(100),
                seller_message TEXT,
                taxes_on_fee DECIMAL(20,2),
                card_id VARCHAR(255),
                card_name VARCHAR(255),
                card_address_line1 TEXT,
                card_address_line2 TEXT,
                card_address_city VARCHAR(255),
                card_address_state VARCHAR(255),
                card_address_country VARCHAR(50),
                card_address_zip VARCHAR(100),
                card_avs_line1_status VARCHAR(100),
                card_avs_zip_status VARCHAR(100),
                card_brand VARCHAR(100),
                card_cvc_status VARCHAR(100),
                card_exp_month VARCHAR(20),
                card_exp_year VARCHAR(20),
                card_fingerprint VARCHAR(255),
                card_funding VARCHAR(100),
                card_issue_country VARCHAR(50),
                card_last4 VARCHAR(20),
                card_tokenization_method VARCHAR(100),
                customer_id VARCHAR(255),
                customer_description TEXT,
                customer_email VARCHAR(255),
                customer_phone VARCHAR(100),
                shipping_name VARCHAR(255),
                shipping_address_line1 TEXT,
                shipping_address_line2 TEXT,
                shipping_address_city VARCHAR(255),
                shipping_address_state VARCHAR(255),
                shipping_address_country VARCHAR(50),
                shipping_address_postal_code VARCHAR(100),
                disputed_amount DECIMAL(20,2),
                dispute_date_utc DATETIME,
                dispute_evidence_due_utc DATETIME,
                dispute_reason VARCHAR(255),
                dispute_status VARCHAR(100),
                invoice_id VARCHAR(255),
                invoice_number VARCHAR(255),
                checkout_session_id VARCHAR(255),
                checkout_custom_field_1_key VARCHAR(255),
                checkout_custom_field_1_value TEXT,
                checkout_custom_field_2_key VARCHAR(255),
                checkout_custom_field_2_value TEXT,
                checkout_custom_field_3_key VARCHAR(255),
                checkout_custom_field_3_value TEXT,
                checkout_line_item_summary TEXT,
                checkout_promotional_consent VARCHAR(20),
                checkout_terms_of_service_consent VARCHAR(20),
                client_reference_id VARCHAR(255),
                payment_link_id VARCHAR(255),
                utm_campaign VARCHAR(255),
                utm_content VARCHAR(255),
                utm_medium VARCHAR(255),
                utm_source VARCHAR(255),
                utm_term VARCHAR(255),
                terminal_location_id VARCHAR(255),
                terminal_reader_id VARCHAR(255),
                application_fee DECIMAL(20,2),
                application_id VARCHAR(255),
                destination VARCHAR(255),
                transfer VARCHAR(255),
                transfer_group VARCHAR(255),
                type_metadata VARCHAR(100)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == "Thera_Ledger_Transactions":
        create_statement = """
            CREATE TABLE IF NOT EXISTS Thera_Ledger_Transactions (
                id VARCHAR(255) PRIMARY KEY,
                description TEXT,
                status VARCHAR(50),
                ledger_id VARCHAR(255),
                effective_date DATETIME,
                posted_at DATETIME,
                metadata TEXT,
                amount_BRL DECIMAL(20,2),
                currency_BRL VARCHAR(10),
                amount_CAD DECIMAL(20,2),
                currency_CAD VARCHAR(10),
                amount_CHF DECIMAL(20,2),
                currency_CHF VARCHAR(10),
                amount_CLP DECIMAL(20,2),
                currency_CLP VARCHAR(10),
                amount_COP DECIMAL(20,2),
                currency_COP VARCHAR(10),
                amount_EUR DECIMAL(20,2),
                currency_EUR VARCHAR(10),
                amount_GBP DECIMAL(20,2),
                currency_GBP VARCHAR(10),
                amount_INR DECIMAL(20,2),
                currency_INR VARCHAR(10),
                amount_MXN DECIMAL(20,2),
                currency_MXN VARCHAR(10),
                amount_NGN DECIMAL(20,2),
                currency_NGN VARCHAR(10),
                amount_PHP DECIMAL(20,2),
                currency_PHP VARCHAR(10),
                amount_UAH DECIMAL(20,2),
                currency_UAH VARCHAR(10),
                amount_USD DECIMAL(20,2),
                currency_USD VARCHAR(10),
                metadata_latestStripeChargeId VARCHAR(255),
                metadata_payInType VARCHAR(50),
                metadata_paymentId VARCHAR(255),
                metadata_paymentMethodId VARCHAR(255),
                metadata_stripeBalanceTrxId VARCHAR(255),
                metadata_stripeExchangeRate DECIMAL(20,10),
                metadata_type VARCHAR(50),
                effective_at DATETIME
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
        
        cursor.execute(create_statement)
        
        # Drop and recreate if columns don't match
        cursor.execute("SHOW COLUMNS FROM Thera_Ledger_Transactions")
        existing_columns = {col[0] for col in cursor.fetchall()}
        expected_columns = {
            'id', 'description', 'status', 'ledger_id', 'effective_date', 'posted_at', 'metadata',
            'amount_BRL', 'currency_BRL', 'amount_CAD', 'currency_CAD', 'amount_CHF', 'currency_CHF',
            'amount_CLP', 'currency_CLP', 'amount_COP', 'currency_COP', 'amount_EUR', 'currency_EUR',
            'amount_GBP', 'currency_GBP', 'amount_INR', 'currency_INR', 'amount_MXN', 'currency_MXN',
            'amount_NGN', 'currency_NGN', 'amount_PHP', 'currency_PHP', 'amount_UAH', 'currency_UAH',
            'amount_USD', 'currency_USD', 'metadata_latestStripeChargeId', 'metadata_payInType',
            'metadata_paymentId', 'metadata_paymentMethodId', 'metadata_stripeBalanceTrxId',
            'metadata_stripeExchangeRate', 'metadata_type', 'effective_at'
        }
        
        if existing_columns != expected_columns:
            log("Table schema mismatch - recreating table...")
            cursor.execute("DROP TABLE Thera_Ledger_Transactions")
            cursor.execute(create_statement)
        return

    if table_name == "Reconciliation_Results":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reconciliation_Results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stripe_id VARCHAR(255),
                ledger_id VARCHAR(255),
                stripe_amount DECIMAL(10,2),
                ledger_amount DECIMAL(10,2),
                stripe_currency VARCHAR(10),
                ledger_currency VARCHAR(10),
                stripe_date DATETIME,
                ledger_date DATETIME,
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stripe_id) REFERENCES Thera_Stripe_Incoming_Transactions(id),
                FOREIGN KEY (ledger_id) REFERENCES Thera_Ledger_Transactions(id)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == "balance_reconciliation_summary":
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_ledger_currency (ledger_id, currency)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

    if table_name == "Thera_Ledger_Accounts":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Thera_Ledger_Accounts (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255),
                description TEXT,
                normal_balance VARCHAR(50),
                currency VARCHAR(10),
                posted_balance DECIMAL(20,2),
                pending_balance DECIMAL(20,2),
                balances_as_of DATETIME,
                lock_version INT,
                ledger_id VARCHAR(255),
                metadata TEXT,
                metadata_companyId VARCHAR(255),
                metadata_type VARCHAR(50),
                metadata_userId VARCHAR(255),
                effective_at DATETIME
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        return

def get_db_connection():
    try:
        return pymysql.connect(**db_params)
    except Exception as e:
        log(f"Database connection error: {str(e)}")
        raise

def connect_with_retry(max_retries=3, delay=5):
    """Attempt to connect to database with retries"""
    for attempt in range(max_retries):
        try:
            log(f"Database connection attempt {attempt + 1} of {max_retries}")
            conn = get_db_connection()
            return conn
        except pymysql.Error as e:
            if attempt == max_retries - 1:  # Last attempt
                raise  # Re-raise the last error
            log(f"Connection failed, retrying in {delay} seconds... Error: {str(e)}")
            time.sleep(delay)

def process_and_upload_file(file_path, source_type):
    conn = None
    cursor = None
    try:
        log(f"Processing file: {file_path}")
        log(f"Source type: {source_type}")
        
        log("Reading CSV file...")
        df = pd.read_csv(file_path)
        log(f"CSV loaded successfully. Shape: {df.shape}")
        
        # Log original columns
        log(f"Columns found: {list(df.columns)}")
        
        # Clean column names
        log("Cleaning column names...")
        df.columns = clean_column_names(df.columns)
        
        # Log cleaned columns
        log(f"Clean columns: {list(df.columns)}")
        
        # Add this logging to check data before any filtering
        log(f"Initial row count: {len(df)}")
        
        # Check for any implicit filtering in the validation step
        validate_columns(df, source_type)
        
        # Add logging after validation
        log(f"Row count after validation: {len(df)}")
        
        # Check for nulls in key columns for Ledger Transactions
        if source_type == 'Thera_Ledger_Transactions':
            key_columns = ['effective_date', 'metadata_type', 'metadata_latestStripeChargeId', 'metadata_paymentId']
            for col in key_columns:
                null_count = df[col].isnull().sum()
                log(f"Null values in {col}: {null_count}")
        
        # Add logging before upload
        log(f"Final row count before upload: {len(df)}")
        
        # Connect to database
        log("Connecting to database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        log("Database connection successful")
        
        # Create table if it doesn't exist
        log(f"Creating/checking table: {source_type}")
        create_table_if_not_exists(cursor, source_type)
        
        # Determinar la columna clave según el tipo de tabla
        key_column = {
            'Thera_Stripe_Balance_Changes': 'balance_transaction_id',
            'Thera_Stripe_Incoming_Transactions': 'id',
            'Thera_Ledger_Transactions': 'id',
            'Thera_Ledger_Accounts': 'id'
        }.get(source_type, 'id')
        
        log(f"Checking for duplicates using key column: {key_column}")
        
        # Verificar duplicados
        cursor.execute(f"SELECT `{key_column}` FROM `{source_type}`")
        existing_keys = {row[0] for row in cursor.fetchall()}
        
        # Preparar datos para inserción
        log("Preparing data for insertion...")
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].replace({pd.NA: None, np.nan: None})
                df[col] = df[col].apply(lambda x: str(x) if pd.notnull(x) else None)
            elif pd.api.types.is_object_dtype(df[col]):
                if col in ['posted_at', 'effective_at', 'effective_date', 'created_date_utc', 'refunded_date_utc']:
                    df[col] = df[col].apply(lambda x: x.replace(' UTC', '') if isinstance(x, str) else x)
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else None)
                else:
                    df[col] = df[col].replace({pd.NA: None, np.nan: None, 'nan': None, 'None': None, '': None})
        
        # Insertar datos
        if len(df) > 0:
            columns = ', '.join(f'`{col}`' for col in df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            
            # Usar REPLACE en lugar de INSERT
            replace_query = f"REPLACE INTO `{source_type}` ({columns}) VALUES ({placeholders})"
            
            data = df.replace({pd.NA: None, np.nan: None}).values.tolist()
            data = [tuple(None if pd.isna(x) else x for x in row) for row in data]
            
            # Insert in batches
            batch_size = 1000
            total_rows = len(data)
            for i in range(0, total_rows, batch_size):
                batch = data[i:i + batch_size]
                cursor.executemany(replace_query, batch)
                conn.commit()
                log(f"Replaced {min(i + batch_size, total_rows)} of {total_rows} rows")
            
            # Obtener conteo de inserciones y actualizaciones
            cursor.execute(f"SELECT COUNT(*) FROM `{source_type}`")
            final_count = cursor.fetchone()[0]
            
            log("Data replacement completed successfully")
            return True, f"Successfully processed {len(df)} records. Final table count: {final_count}"
        else:
            return True, "No records to process"
            
    except Exception as e:
        log(f"Error during data processing/insertion: {str(e)}")
        if conn:
            conn.rollback()
        return False, str(e)
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def perform_reconciliation():
    """Wrapper for reconciliation service"""
    try:
        log("Starting reconciliation process...")
        success, result = service_reconciliation()
        if success:
            log("Reconciliation completed successfully")
            return True, result
        else:
            log(f"Reconciliation failed: {result}")
            return False, result
    except Exception as e:
        log(f"Error during reconciliation: {str(e)}")
        return False, str(e)

def get_source_data(source_id):
    """Get source data and associated files"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get the source data
        cursor.execute("""
            SELECT * FROM Thera_Ledger_Transactions 
            WHERE id = %s
            LIMIT 1
        """, (source_id,))
        source = cursor.fetchone()
        
        if not source:
            # Return a valid JSON structure even when no data is found
            return True, json.dumps({
                "message": "No data found",
                "file_urls": [],
                "data": None
            })
        
        # Convert any non-serializable types to strings
        serializable_source = {}
        for key, value in source.items():
            if isinstance(value, (datetime, pd.Timestamp)):
                serializable_source[key] = value.isoformat()
            else:
                serializable_source[key] = value
        
        # Create the response structure
        response = {
            "message": "Data found",
            "file_urls": [],  # We'll add file tracking later
            "data": serializable_source
        }
        
        return True, json.dumps(response)
    except Exception as e:
        log(f"Error in get_source_data: {str(e)}")
        # Return a valid JSON structure even on error
        return True, json.dumps({
            "message": f"Error: {str(e)}",
            "file_urls": [],
            "data": None
        })
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def upload_to_mysql(df, table_name):
    try:
        # Add logging for the upload process
        log(f"Starting upload for {len(df)} rows")
        
        # Get column names and create placeholders
        columns = df.columns.tolist()
        placeholders = ', '.join(['%s'] * len(columns))
        
        # Create the insert query
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert DataFrame to list of tuples
        values = df.fillna('').values.tolist()
        log(f"Prepared {len(values)} rows for upload")
        
        # Execute the insert
        cursor.executemany(insert_query, values)
        conn.commit()
        
        # Verify the upload
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        final_count = cursor.fetchone()[0]
        log(f"Final row count in table: {final_count}")
        
        return True
    except Exception as e:
        log(f"Error during upload: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Process files and perform reconciliation')
    parser.add_argument('--file', help='Path to the file to process')
    parser.add_argument('--source', help='Source type of the data')
    parser.add_argument('--reconcile', action='store_true', help='Perform reconciliation')
    parser.add_argument('--get-source', action='store_true', help='Get source data')
    parser.add_argument('--source-id', help='Source ID to fetch')
    
    args = parser.parse_args()
    log(f"Arguments received: {args}")
    
    if args.get_source and args.source_id:
        success, message = get_source_data(args.source_id)
        if not success:
            print(f"Error fetching source: {message}", file=sys.stderr)
            sys.exit(1)
        print(message)
        sys.exit(0)
    
    if args.reconcile:
        success, result = perform_reconciliation()
        if not success:
            print(f"Error during reconciliation: {result}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result))
        sys.exit(0)
    
    if args.file and args.source:
        success, message = process_and_upload_file(args.file, args.source)
        if not success:
            print(f"Error processing file: {message}", file=sys.stderr)
            sys.exit(1)
        print(message)
        sys.exit(0)
    
    print("No valid arguments provided", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main() 