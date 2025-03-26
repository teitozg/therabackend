import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

db_params = {
    "host": os.getenv('DB_HOST', '127.0.0.1'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'Atenas9democraci.'),
    "database": os.getenv('DB_NAME', 'thera_final_database'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "connect_timeout": 180
}

def check_tables():
    try:
        conn = pymysql.connect(**db_params)
        cursor = conn.cursor()
        
        # Check Stripe source table columns
        print("\nStripe source table columns:")
        cursor.execute("SELECT * FROM Thera_Stripe_Incoming_Transactions LIMIT 1")
        stripe_columns = [desc[0] for desc in cursor.description]
        print("Stripe columns:", stripe_columns)
        
        # Check Ledger source table columns
        print("\nLedger source table columns:")
        cursor.execute("SELECT * FROM Thera_Ledger_Transactions LIMIT 1")
        ledger_columns = [desc[0] for desc in cursor.description]
        print("Ledger columns:", ledger_columns)
        
        # Check started_matches structure
        print("\nChecking started_matches table structure:")
        cursor.execute("SHOW CREATE TABLE started_matches")
        result = cursor.fetchone()
        if result:
            print(result[1])
        else:
            print("Table started_matches does not exist")
            
        # Check succeeded_matches structure
        print("\nChecking succeeded_matches table structure:")
        cursor.execute("SHOW CREATE TABLE succeeded_matches")
        result = cursor.fetchone()
        if result:
            print(result[1])
        else:
            print("Table succeeded_matches does not exist")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_tables() 