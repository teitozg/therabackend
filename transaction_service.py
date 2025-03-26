import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os
import sys
import json
from decimal import Decimal

load_dotenv()

# MySQL Connection Parameters
db_params = {
    "host": os.getenv('DB_HOST', '127.0.0.1'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'Atenas9democraci.'),
    "database": os.getenv('DB_NAME', 'thera_final_database'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "connect_timeout": 180
}

def log(message):
    print(f"[{datetime.now().isoformat()}] {message}", file=sys.stderr)

# Add this custom JSON encoder
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_transactions(table_name="started_matches"):
    """Get transactions from specified table"""
    try:
        if table_name not in ["started_matches", "succeeded_matches"]:
            raise ValueError("Invalid table name")
            
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute(f"""
            SELECT 
                stripe_id,
                stripe_converted_amount,
                stripe_converted_currency,
                stripe_created_date_utc,
                stripe_customer_id,
                stripe_customer_email,
                stripe_paymentintent_id,
                stripe_mode,
                stripe_payment_source_type,
                stripe_seller_message,
                stripe_card_brand,
                stripe_fee,
                merge_source
            FROM {table_name}
            WHERE merge_source != 'ledger_only'
            ORDER BY stripe_created_date_utc DESC
        """)
        
        transactions = cursor.fetchall()
        
        # Convert datetime objects to strings
        for tx in transactions:
            if tx['stripe_created_date_utc']:
                tx['stripe_created_date_utc'] = tx['stripe_created_date_utc'].isoformat()
        
        return True, json.dumps(transactions, cls=DecimalEncoder)
        
    except Exception as e:
        log(f"Error fetching transactions: {str(e)}")
        return False, str(e)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    success, result = get_transactions()
    if success:
        print(result)
        sys.exit(0)
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 