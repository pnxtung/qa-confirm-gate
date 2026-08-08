import sqlite3
import os
import requests
import json
from backend.core.config import DB_PATH, SUPABASE_URL, SUPABASE_KEY

def migrate_all():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[MIGRATION ERROR] SUPABASE_URL or SUPABASE_KEY is missing!")
        return

    if not os.path.exists(DB_PATH):
        print(f"[MIGRATION ERROR] {DB_PATH} does not exist!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    tables = ["users", "teams", "models", "master_checklist", "model_checklist", "document_versions", "document_files"]

    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                print(f"[MIGRATION] Table '{table}' is empty, skipping.")
                continue

            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
            resp = requests.post(url, headers=headers, data=json.dumps(rows))
            if resp.status_code in (200, 201):
                print(f"[MIGRATION SUCCESS] Migrated {len(rows)} rows to Supabase table '{table}'")
            else:
                print(f"[MIGRATION ERROR] Failed table '{table}': {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[MIGRATION EXCEPTION] Table '{table}': {e}")

    conn.close()

if __name__ == "__main__":
    migrate_all()
