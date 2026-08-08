import sqlite3
import os
import re
from datetime import datetime

SQLITE_DB = 'Local - Demo App/data/database.db'
OUTPUT_SQL = 'postgres_migration.sql'

def sqlite_to_postgres_type(sql):
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', sql, flags=re.IGNORECASE)
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY', 'SERIAL PRIMARY KEY', sql, flags=re.IGNORECASE)
    sql = re.sub(r'CREATE TABLE "([^"]+)"', r'CREATE TABLE \1', sql, flags=re.IGNORECASE)
    return sql

def escape_string(s):
    if s is None:
        return 'NULL'
    if isinstance(s, (int, float)):
        return str(s)
    
    s = str(s)
    
    # Check if string is in HH:MM:SS MM/DD/YYYY format and convert it
    try:
        if len(s) == 19 and s.count(':') == 2 and s.count('/') == 2 and s[2] == ':':
            # e.g. "06:16:12 07/11/2026"
            dt = datetime.strptime(s, "%H:%M:%S %m/%d/%Y")
            s = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
        
    # Escape single quotes
    s = s.replace("'", "''")
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    return f"'{s}'"

def main():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found!")
        return

    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()

    with open(OUTPUT_SQL, 'w', encoding='utf-8') as f:
        f.write("-- ========================================================\n")
        f.write("-- POSTGRESQL MIGRATION SCRIPT\n")
        f.write("-- ========================================================\n\n")

        # Enforce table order to satisfy foreign key constraints
        table_order_pref = [
            'app_config', 'site_content', 'access_logs', 'users', 'teams', 'master_checklist',
            'models', 'model_checklist', 'document_versions', 'confirmation_progress', 'document_files'
        ]
        
        table_dict = {row['name']: row for row in tables}
        ordered_table_names = []
        for name in table_order_pref:
            if name in table_dict:
                ordered_table_names.append(name)
        
        # Add any tables that were not in the preference list
        for name in table_dict:
            if name not in ordered_table_names:
                ordered_table_names.append(name)
                
        table_names = ordered_table_names

        for table_name in table_names:
            row = table_dict[table_name]
            create_sql = row['sql']
            pg_sql = sqlite_to_postgres_type(create_sql)
            f.write(f"DROP TABLE IF EXISTS {table_name} CASCADE;\n")
            f.write(f"{pg_sql};\n\n")

        for table_name in table_names:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if not rows:
                continue
            
            f.write(f"-- Data for {table_name}\n")
            f.write(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;\n")
            
            columns = rows[0].keys()
            col_names = ", ".join(columns)
            
            for row in rows:
                values = [escape_string(row[col]) for col in columns]
                val_str = ", ".join(values)
                f.write(f"INSERT INTO {table_name} ({col_names}) VALUES ({val_str});\n")
            
            f.write("\n")

        f.write("-- ========================================================\n")
        f.write("-- RESET SEQUENCES\n")
        f.write("-- ========================================================\n")
        for table_name in table_names:
            if table_name == 'access_logs':
                continue
            f.write(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table_name};\n")
            
        f.write("\n")
        
        f.write("-- ========================================================\n")
        f.write("-- SECURITY SETTINGS\n")
        f.write("-- ========================================================\n")
        for table_name in table_names:
            f.write(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY;\n")
            
        f.write("\nGRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;\n")
        f.write("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;\n")

    print(f"Migration script successfully generated at {OUTPUT_SQL}")
    conn.close()

if __name__ == "__main__":
    main()
