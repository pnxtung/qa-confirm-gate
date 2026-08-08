import psycopg2
import os

DB_URL = "postgresql://postgres:qacfpnx123%40@db.tlbdkjboznmtnazhjtxh.supabase.co:5432/postgres"
SQL_FILE = "postgres_migration.sql"

def main():
    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        return

    print("Connecting to Supabase PostgreSQL...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print(f"Reading {SQL_FILE}...")
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        print("Executing migration script. This may take a few seconds...")
        cursor.execute(sql_script)
        
        print("Migration successful!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
