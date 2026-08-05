from fastapi import APIRouter, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.database import get_db
from backend.core.security import create_token
import sqlite3

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

# Render trang Đăng ký tài khoản
@router.get("/register")
async def get_register(request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams WHERE active = 'Yes'")
    active_teams = [dict(t) for t in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse(request=request, name="user_register.html", context={"active_teams": active_teams})

# Xử lý form Đăng ký (Trạng thái Pending)
@router.post("/register")
async def post_register(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    team: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (fullname, email, team, username, password, access_role) VALUES (?, ?, ?, ?, ?, ?)",
            (fullname, email, team, username, password, "Pending")
        )
        conn.commit()
        conn.close()
        StorageAdapter.sync_database()
    except sqlite3.IntegrityError:
        try: conn.close()
        except: pass
        return templates.TemplateResponse(request=request, name="user_register.html", context={"error": "Employee ID already exists."})
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

# Render trang Đăng nhập
@router.get("/login")
async def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

# Xử lý form Đăng nhập và cấp Token
@router.post("/login")
async def post_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or user["password"] != password:
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid credentials"})
        
    if user["access_role"] == "Pending":
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Waiting for Admin to approve access"})

    token = create_token(user["username"])
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response

# Đăng xuất
@router.get("/logout")
@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response
