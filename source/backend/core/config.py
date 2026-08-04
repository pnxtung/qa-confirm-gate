import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = os.getenv("SECRET_KEY", "default_insecure_secret_key")

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


