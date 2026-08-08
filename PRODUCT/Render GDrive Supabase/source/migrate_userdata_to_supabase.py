import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "pnx-userdata")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_KEY in .env file.")
    exit(1)

# Path to local User Data directory
user_data_path = os.path.abspath(r"d:\PNX App\QA Confirm Gate\PRODUCT\Local - Demo App\User Data")

if not os.path.exists(user_data_path):
    print(f"Error: User Data folder not found at {user_data_path}")
    exit(1)

def _clean_parts(rel_path: str):
    clean = rel_path.replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p and p != ".." and p != "."]
    if len(parts) >= 2 and parts[0] == "User Data" and parts[1] == "MP readiness data":
        parts = parts[2:]
    elif len(parts) >= 1 and (parts[0] == "User Data" or parts[0] == "MP readiness data"):
        parts = parts[1:]
    return parts

def upload_file_to_supabase(local_path: str, rel_path: str) -> bool:
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
    
    # Determine Content-Type based on extension
    if local_path.endswith(".html"):
        headers["Content-Type"] = "text/html; charset=utf-8"
    
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        response = requests.post(url, headers=headers, data=data)
        if response.status_code in (200, 201):
            print(f"[OK] Uploaded: {storage_path}")
            return True
        else:
            print(f"[FAIL] {storage_path} - {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception uploading {storage_path}: {e}")
        return False

print(f"Starting migration of files from '{user_data_path}' to Supabase bucket '{SUPABASE_STORAGE_BUCKET}'...")

success_count = 0
fail_count = 0

for root, _, files in os.walk(user_data_path):
    for file in files:
        local_path = os.path.join(root, file)
        rel_path = os.path.relpath(local_path, start=os.path.dirname(user_data_path))
        
        if upload_file_to_supabase(local_path, rel_path):
            success_count += 1
        else:
            fail_count += 1

print("\n--- MIGRATION COMPLETE ---")
print(f"Successful uploads: {success_count}")
print(f"Failed uploads: {fail_count}")
