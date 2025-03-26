import os
from dotenv import load_dotenv
import pymysql
import sys

load_dotenv()

def log(message):
    print(f"[LOG] {message}", file=sys.stderr)

db_params = {
    "host": "127.0.0.1",  # Connect to local proxy
    "user": "root",
    "password": "Atenas9democraci.",
    "database": "thera_final_database",
    "port": 3306,
    "connect_timeout": 60
}

def test_connection():
    try:
        log("Attempting to connect to database...")
        log(f"Connecting through Cloud SQL Proxy on {db_params['host']}:{db_params['port']}")
        conn = pymysql.connect(**db_params)
        log("Successfully connected!")
        
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        log("\nAvailable tables:")
        for table in tables:
            log(f"- {table[0]}")
            
    except Exception as e:
        log(f"Connection failed: {str(e)}")
        log(f"Connection parameters (excluding password): {dict((k,v) for k,v in db_params.items() if k != 'password')}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            log("Connection closed")

if __name__ == "__main__":
    test_connection() 