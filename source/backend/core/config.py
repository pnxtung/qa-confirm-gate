import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "default_insecure_secret_key")
DB_PATH = os.getenv("DB_PATH", "backend/data/database.db")
MP_READINESS_DATA_PATH = os.getenv("MP_READINESS_DATA_PATH", "../User Data/MP readiness data")
V00_TEMPLATES_PATH = os.getenv("V00_TEMPLATES_PATH", "../User Data/V00_templates")
