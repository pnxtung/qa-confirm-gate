from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sqlite3

from backend.routers.user_auth import router as user_auth_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.admin_management import router as admin_management_router
from backend.routers.model_config import router as model_config_router
from backend.routers.upload_document import router as upload_document_router
from backend.core.config import DB_PATH, MP_READINESS_DATA_PATH, V00_TEMPLATES_PATH, STORAGE_DB_PROVIDERS
from backend.core.gdrive_storage import restore_database_from_gdrive

app = FastAPI(title="QA Confirm Gate")

# Khởi tạo thư mục vật lý thiết yếu
os.makedirs("frontend/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Chèn dữ liệu mặc định lúc khởi động (Tài khoản Admin và Teams)
@app.on_event("startup")
async def startup_event():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(MP_READINESS_DATA_PATH, exist_ok=True)
    os.makedirs(V00_TEMPLATES_PATH, exist_ok=True)

    # Tải bản database.db mới nhất từ Google Drive nếu provider là GDRIVE
    if "GDRIVE" in STORAGE_DB_PROVIDERS:
        restore_database_from_gdrive()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Thao tác đảm bảo khởi tạo CSDL cục bộ nếu chưa có
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT, email TEXT, team TEXT, username TEXT UNIQUE, password TEXT, access_role TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, active TEXT DEFAULT 'Yes'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, model_type TEXT, customer TEXT, line TEXT,
            mp1st_date TEXT, mp1st_qty INTEGER, ship1st_date TEXT, ship1st_qty INTEGER, status TEXT DEFAULT 'Active',
            activate TEXT DEFAULT 'Yes', sort_order INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, team TEXT, level_1 TEXT, level_2 TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, model_id INTEGER, team TEXT, level_1 TEXT, level_2 TEXT, locked_by TEXT, locked_at INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, model_checklist_id INTEGER, version_no TEXT, status TEXT DEFAULT 'Draft',
            is_latest INTEGER DEFAULT 1, content TEXT, reason TEXT, updated_at TEXT, approver_username TEXT, approved_at TEXT, uploader_username TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER, filename TEXT, filepath TEXT, uploaded_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            id INTEGER PRIMARY KEY, config_updated_at INTEGER, last_updated_by TEXT
        )
    """)
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE username = 'ADMINPNX'")
    if not cursor.fetchone():
        cursor.execute("DELETE FROM users WHERE username = 'admin' OR username = 'ADMIN'")
        cursor.execute("INSERT INTO users (fullname, email, team, username, password, access_role) VALUES (?, ?, ?, ?, ?, ?)",
                       ("Admin", "admin@domain.com", "Admin", "ADMINPNX", "adminpnx", "Admin"))
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM teams")
    if cursor.fetchone()[0] == 0:
        default_teams = ['App Insp', 'CS', 'DQA', 'Final Insp', 'Integrated', 'OQA', 'Planning', 'Process DEV', 'Production', 'RnD', 'SQA', 'Tech 1', 'Tech 2']
        for t in default_teams:
            cursor.execute("INSERT INTO teams (name, active) VALUES (?, ?)", (t, 'Yes'))
        conn.commit()
        
    conn.close()

# Gắn kết tất cả routers tính năng
app.include_router(dashboard_router)
app.include_router(user_auth_router)
app.include_router(admin_management_router)
app.include_router(model_config_router)
app.include_router(upload_document_router)
