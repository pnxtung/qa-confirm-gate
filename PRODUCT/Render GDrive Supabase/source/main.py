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
