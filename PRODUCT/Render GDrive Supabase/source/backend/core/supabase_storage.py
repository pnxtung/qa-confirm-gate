import os
import logging
import requests
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
