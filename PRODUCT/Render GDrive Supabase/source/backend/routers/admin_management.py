from fastapi import APIRouter, Request, Form, status, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
import time
from backend.core.database import get_db, check_pessimistic_admin_lock
from backend.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

# Render trang Quản lý Admin (Chỉ dành cho Admin)
@router.get("/admin")
async def get_admin(request: Request):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    
    # Check trạng thái khóa chỉnh sửa
    can_edit = (user["access_role"] == "Admin")
    locked_by = ""
    locked_at = 0
    if can_edit:
        cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 2")
        row = cursor.fetchone()
        current_time = int(time.time())
        if row and row['last_updated_by'] and current_time - (row['config_updated_at'] or 0) < 600:
            locked_by = row['last_updated_by']
            locked_at = row['config_updated_at']
            
    cursor.execute("SELECT * FROM users WHERE username != 'ADMINPNX'")
    users = [dict(u) for u in cursor.fetchall()]
    cursor.execute("SELECT * FROM teams")
    teams = [dict(t) for t in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="user_management.html",
        context={
            "users": users, 
            "teams": teams, 
            "current_user": dict(user),
            "locked_by": locked_by, 
            "locked_at": locked_at, 
            "server_time": int(time.time()), 
            "can_edit_backend": can_edit
        }
    )

# Lưu danh sách Teams mới nhất
@router.post("/admin/save_teams")
@router.post("/admin/bulk_update_teams")
async def save_teams(
    request: Request,
    team_name: List[str] = Form(default=[]),
    team_active: List[str] = Form(default=[])
):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_admin_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
        
    try:
        cursor.execute("DELETE FROM teams")
        for i in range(len(team_name)):
            t_name = team_name[i].strip()
            if not t_name: continue
            t_active = team_active[i] if i < len(team_active) else 'Yes'
            cursor.execute("INSERT INTO teams (name, active) VALUES (?, ?)", (t_name, t_active))
            
        cursor.execute("UPDATE users SET team = 'Others' WHERE team NOT IN (SELECT name FROM teams)")
        conn.commit()
        conn.close()
        StorageAdapter.sync_database()
        return {"success": True}
    except Exception as e:
        print("Error saving teams:", e)
        try: conn.close()
        except: pass
        return {"success": False, "error": str(e)}

# Lưu hàng loạt thay đổi (Thêm mới và Cập nhật) User
@router.post("/admin/bulk_update")
async def bulk_update(
    request: Request,
    user_id: List[int] = Form(default=[]),
    fullname: List[str] = Form(default=[]),
    email: List[str] = Form(default=[]),
    team: List[str] = Form(default=[]),
    username: List[str] = Form(default=[]),
    password: List[str] = Form(default=[]),
    access_role: List[str] = Form(default=[])
):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_admin_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
        
    try:
        for i in range(len(user_id)):
            if user_id[i] == 0:
                cursor.execute("""
                    INSERT INTO users (fullname, email, team, username, password, access_role)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (fullname[i], email[i], team[i], username[i], password[i], access_role[i]))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET fullname=?, email=?, team=?, username=?, password=?, access_role=?
                    WHERE id=?
                """, (fullname[i], email[i], team[i], username[i], password[i], access_role[i], user_id[i]))
        conn.commit()
        conn.close()
        StorageAdapter.sync_database()
        return {"success": True}
    except Exception:
        try: conn.close()
        except: pass
        conn = get_db()
        cursor = conn.cursor()
        
        can_edit = (user["access_role"] == "Admin")
        locked_by = ""
        locked_at = 0
        if can_edit:
            cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 2")
            row = cursor.fetchone()
            current_time = int(time.time())
            if row and row['last_updated_by'] and current_time - (row['config_updated_at'] or 0) < 600:
                locked_by = row['last_updated_by']
                locked_at = row['config_updated_at']
                
        cursor.execute("SELECT * FROM users WHERE username != 'ADMINPNX'")
        users = [dict(u) for u in cursor.fetchall()]
        cursor.execute("SELECT * FROM teams")
        teams = [dict(t) for t in cursor.fetchall()]
        conn.close()
        return templates.TemplateResponse("user_management.html", {
            "request": request, "users": users, "teams": teams,
            "locked_by": locked_by, "locked_at": locked_at, "server_time": int(time.time()),
            "can_edit_backend": can_edit, "error": "Employee ID already exists. Updates were not saved.", 
            "current_user": user
        })

# Xóa một User
@router.post("/admin/delete_user/{target_id}")
async def delete_user(request: Request, target_id: int):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_admin_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
        
    cursor.execute("DELETE FROM users WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()
    StorageAdapter.sync_database()
    return {"success": True}

# Bật khóa sửa Admin Management
@router.post("/api/admin/lock")
async def api_admin_lock(request: Request):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return Response(status_code=403)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 2")
    row = cursor.fetchone()
    current_time = int(time.time())
    
    if row and row['last_updated_by'] and row['last_updated_by'] != user['fullname'] and current_time - (row['config_updated_at'] or 0) < 600:
        conn.close()
        return {"success": False, "error": f"{row['last_updated_by']} đang chỉnh sửa Admin Management, bạn không thể thao tác vào lúc này."}
        
    cursor.execute("INSERT OR REPLACE INTO app_config (id, config_updated_at, last_updated_by) VALUES (2, ?, ?)", (current_time, user['fullname']))
    conn.commit()
    conn.close()
    return {"success": True, "locked_at": current_time}

# Tắt khóa sửa Admin Management
@router.post("/api/admin/unlock")
async def api_admin_unlock(request: Request):
    user = get_current_user(request)
    if not user:
        return Response(status_code=403)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT last_updated_by FROM app_config WHERE id = 2")
    row = cursor.fetchone()
    if row and row['last_updated_by'] == user['fullname']:
        cursor.execute("UPDATE app_config SET last_updated_by = NULL, config_updated_at = 0 WHERE id = 2")
        conn.commit()
    conn.close()
    return {"success": True}
