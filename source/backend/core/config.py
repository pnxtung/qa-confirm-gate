import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = os.getenv("SECRET_KEY", "default_insecure_secret_key")

# Storage Switches
raw_db_providers = os.getenv("STORAGE_DB_PROVIDER", "LOCAL")
STORAGE_DB_PROVIDERS = [p.strip().upper() for p in raw_db_providers.split(",") if p.strip()]

raw_userdata_providers = os.getenv("STORAGE_USERDATA_PROVIDER", "LOCAL")
STORAGE_USERDATA_PROVIDERS = [p.strip().upper() for p in raw_userdata_providers.split(",") if p.strip()]

SYNC_MODE = os.getenv("SYNC_MODE", "ASYNC").strip().upper()

# Local Paths
raw_db_path = os.getenv("DB_PATH", "../data/database.db")
if not os.path.isabs(raw_db_path):
    DB_PATH = os.path.abspath(os.path.join(BASE_DIR, raw_db_path))
else:
    DB_PATH = raw_db_path

raw_mp_path = os.getenv("MP_READINESS_DATA_PATH", "../User Data/MP readiness data")
if not os.path.isabs(raw_mp_path):
    MP_READINESS_DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, raw_mp_path))
else:
    MP_READINESS_DATA_PATH = raw_mp_path

raw_tpl_path = os.getenv("V00_TEMPLATES_PATH", "../User Data/V00_templates")
if not os.path.isabs(raw_tpl_path):
    V00_TEMPLATES_PATH = os.path.abspath(os.path.join(BASE_DIR, raw_tpl_path))
else:
    V00_TEMPLATES_PATH = raw_tpl_path

# Google Drive Cloud Params
GDRIVE_CREDENTIALS_FILE = os.getenv("GDRIVE_CREDENTIALS_FILE", "backend/core/credentials.json")
if not os.path.isabs(GDRIVE_CREDENTIALS_FILE):
    GDRIVE_CREDENTIALS_FILE = os.path.abspath(os.path.join(BASE_DIR, GDRIVE_CREDENTIALS_FILE))
GDRIVE_ROOT_FOLDER_ID = os.getenv("GDRIVE_ROOT_FOLDER_ID", "")
GDRIVE_DB_FILE_ID = os.getenv("GDRIVE_DB_FILE_ID", "")

# Supabase Cloud Params
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "pnx-userdata")



