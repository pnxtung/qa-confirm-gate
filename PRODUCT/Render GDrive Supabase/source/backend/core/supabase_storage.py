import os
import logging
import requests
import sqlite3
from backend.core.config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_STORAGE_BUCKET
)

logger = logging.getLogger(__name__)

def _clean_parts(rel_path: str):
    clean = rel_path.replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p and p != ".." and p != "."]
    if len(parts) >= 2 and parts[0] == "User Data" and parts[1] == "MP readiness data":
        parts = parts[2:]
    elif len(parts) >= 1 and (parts[0] == "User Data" or parts[0] == "MP readiness data"):
        parts = parts[1:]
    return parts

def upload_html_to_supabase(rel_path: str, html_content: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("[SUPABASE] SUPABASE_URL or SUPABASE_KEY missing!")
        return False

    parts = _clean_parts(rel_path)
    if not parts:
        return False
    storage_path = "/".join(parts)

    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{storage_path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "text/html; charset=utf-8",
        "x-upsert": "true"
    }

    try:
        response = requests.post(url, headers=headers, data=html_content.encode("utf-8"))
        if response.status_code in (200, 201):
            logger.info(f"[SUPABASE STORAGE] Successfully uploaded {storage_path}")
            return True
        else:
            logger.error(f"[SUPABASE STORAGE ERROR] {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[SUPABASE UPLOAD EXCEPTION] {e}")
        return False

def read_html_from_supabase(rel_path: str) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return ""

    parts = _clean_parts(rel_path)
    if not parts:
        return ""
    storage_path = "/".join(parts)

    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{storage_path}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            auth_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/authenticated/{SUPABASE_STORAGE_BUCKET}/{storage_path}"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            auth_resp = requests.get(auth_url, headers=headers, timeout=10)
            if auth_resp.status_code == 200:
                return auth_resp.text
    except Exception as e:
        logger.error(f"[SUPABASE READ EXCEPTION] {e}")

    return ""

def upload_file_to_supabase(local_path: str, rel_path: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY or not os.path.exists(local_path):
        return False

    parts = _clean_parts(rel_path)
    if not parts:
        return False
    storage_path = "/".join(parts)

    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{storage_path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "x-upsert": "true"
    }

    try:
        with open(local_path, "rb") as f:
            data = f.read()
        response = requests.post(url, headers=headers, data=data)
        if response.status_code in (200, 201):
            logger.info(f"[SUPABASE FILE STORAGE] Uploaded file {storage_path}")
            return True
        else:
            logger.error(f"[SUPABASE FILE ERROR] {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[SUPABASE FILE EXCEPTION] {e}")
        return False

def init_supabase_defaults():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    # 1. Insert ADMINPNX user into Supabase users table
    try:
        user_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/users"
        user_data = [{
            "fullname": "Admin",
            "email": "admin@domain.com",
            "team": "Admin",
            "username": "ADMINPNX",
            "password": "adminpnx",
            "access_role": "Admin"
        }]
        requests.post(user_url, headers=headers, json=user_data, timeout=5)
    except Exception as e:
        logger.error(f"[SUPABASE INIT USER ERROR] {e}")

    # 2. Insert Others team if teams table is empty
    try:
        teams_check_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/teams?select=id"
        check_resp = requests.get(teams_check_url, headers=headers, timeout=5)
        if check_resp.status_code == 200 and len(check_resp.json()) == 0:
            teams_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/teams"
            team_data = [{"name": "Others", "active": "Yes"}]
            requests.post(teams_url, headers=headers, json=team_data, timeout=5)
    except Exception as e:
        logger.error(f"[SUPABASE INIT TEAM ERROR] {e}")

def sync_table_to_supabase(table_name: str, records: list) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY or not records:
        return False
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    try:
        resp = requests.post(url, headers=headers, json=records, timeout=10)
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error(f"[SUPABASE TABLE SYNC ERROR] {table_name}: {e}")
        return False

def fetch_table_from_supabase(table_name: str) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"[SUPABASE TABLE FETCH ERROR] {table_name}: {e}")
    return []

def restore_database_from_supabase(db_path: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ["users", "teams", "models", "master_checklist", "model_checklist", "document_versions", "document_files"]

    for table in tables:
        rows = fetch_table_from_supabase(table)
        if not rows:
            continue
        try:
            cols = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            cursor.execute(f"DELETE FROM {table}")
            for r in rows:
                cursor.execute(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", [r[c] for c in cols])
            conn.commit()
            logger.info(f"[SUPABASE RESTORE] Restored {len(rows)} rows into local table '{table}'")
        except Exception as e:
            logger.error(f"[SUPABASE RESTORE ERROR] {table}: {e}")

    conn.close()

def sync_database_to_supabase(db_path: str):
    if not SUPABASE_URL or not SUPABASE_KEY or not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = ["users", "teams", "models", "master_checklist", "model_checklist", "document_versions", "document_files"]

    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                sync_table_to_supabase(table, rows)
        except Exception as e:
            logger.error(f"[SUPABASE FULL DB SYNC ERROR] {table}: {e}")

    conn.close()
