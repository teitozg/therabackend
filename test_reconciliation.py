import pymysql
import sys
import json

def log(message):
    print(f"[LOG] {message}", file=sys.stderr)

db_params = {
    "host": "35.185.8.133",
    "user": "root",
    "password": "Atenas9democraci.",
    "database": "thera_final_database",
    "port": 3306
}

try:
    log("Connecting to database...")
    conn = pymysql.connect(**db_params)
    cursor = conn.cursor()
    
    # Check Stripe table columns
    log("\nChecking Stripe table columns...")
    cursor.execute("DESCRIBE Thera_Stripe_Incoming_Transactions")
    stripe_columns = cursor.fetchall()
    log("Stripe table columns:")
    for col in stripe_columns:
        log(f"- {col[0]} ({col[1]})")
    
    # Check Ledger table columns
    log("\nChecking Ledger table columns...")
    cursor.execute("DESCRIBE Thera_Ledger_Transactions")
    ledger_columns = cursor.fetchall()
    log("Ledger table columns:")
    for col in ledger_columns:
        log(f"- {col[0]} ({col[1]})")
    
    # Get sample data with correct column names
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    log("\nFetching sample data...")
    cursor.execute("SELECT * FROM Thera_Stripe_Incoming_Transactions LIMIT 1")
    stripe_sample = cursor.fetchone()
    log(f"Stripe sample row: {json.dumps(stripe_sample, default=str)}")
    
    cursor.execute("SELECT * FROM Thera_Ledger_Transactions LIMIT 1")
    ledger_sample = cursor.fetchone()
    log(f"Ledger sample row: {json.dumps(ledger_sample, default=str)}")
    
except Exception as e:
    log(f"Error: {str(e)}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close() 