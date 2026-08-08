from fastapi import APIRouter, Request, Form, status, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
import time
from backend.core.database import get_db, check_pessimistic_admin_lock
from backend.core.security import get_current_user
from backend.core.storage_adapter import StorageAdapter

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
async def bulk_update(request: Request):
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
        form_data = await request.form()
        user_ids = form_data.getlist("user_id")
        fullnames = form_data.getlist("fullname")
        emails = form_data.getlist("email")
        teams = form_data.getlist("team")
        usernames = form_data.getlist("username")
        passwords = form_data.getlist("password")
        access_roles = form_data.getlist("access_role")

        # 1. Load existing non-ADMINPNX users from CSDL before making any modifications
        cursor.execute("SELECT id, username FROM users WHERE username != 'ADMINPNX'")
        existing_db_users = {row[1].strip().lower(): row[0] for row in cursor.fetchall() if row[1]}

        # 2. Check for duplicate usernames within the submitted form AND against existing database users
        seen_in_form = set()
        for i in range(max(len(usernames), len(fullnames))):
            u_username = usernames[i].strip() if i < len(usernames) else ""
            if not u_username or u_username.upper() == 'ADMINPNX':
                continue
            
            clean_u = u_username.lower()
            curr_id = int(user_ids[i]) if (i < len(user_ids) and str(user_ids[i]).isdigit()) else 0

            # Duplicate inside submitted form itself
            if clean_u in seen_in_form:
                conn.close()
                return {"success": False, "error": f"Employee ID already exists: {u_username}"}
            seen_in_form.add(clean_u)

            # Duplicate against existing database users (if new user row or changed to an ID belonging to another user)
            if clean_u in existing_db_users:
                owner_id = existing_db_users[clean_u]
                if curr_id == 0:
                    # User imported from Excel (or newly typed) but username exists. Map it to existing user.
                    pass
                elif owner_id != curr_id:
                    conn.close()
                    return {"success": False, "error": f"Employee ID already exists: {u_username}"}

        # 3. All validations passed! Perform database updates and inserts
        submitted_user_ids = []
        for i in range(max(len(usernames), len(fullnames))):
            u_fullname = fullnames[i].strip() if i < len(fullnames) else ""
            u_email = emails[i].strip() if i < len(emails) else ""
            u_team = teams[i].strip() if i < len(teams) else "Others"
            u_username = usernames[i].strip() if i < len(usernames) else ""
            u_password = passwords[i].strip() if i < len(passwords) else "123456"
            u_access = access_roles[i].strip() if i < len(access_roles) else "Pending"
            curr_id = int(user_ids[i]) if (i < len(user_ids) and str(user_ids[i]).isdigit()) else 0

            if not u_username or u_username.upper() == 'ADMINPNX':
                continue

            clean_u = u_username.lower()
            if curr_id == 0 and clean_u in existing_db_users:
                curr_id = existing_db_users[clean_u]

            if curr_id > 0:
                cursor.execute("""
                    UPDATE users 
                    SET fullname=?, email=?, team=?, username=?, password=?, access_role=?
                    WHERE id=?
                """, (u_fullname, u_email, u_team, u_username, u_password, u_access, curr_id))
                submitted_user_ids.append(curr_id)
            else:
                cursor.execute("""
                    INSERT INTO users (fullname, email, team, username, password, access_role)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (u_fullname, u_email, u_team, u_username, u_password, u_access))
                submitted_user_ids.append(cursor.lastrowid)

        # Delete any users removed from table
        if submitted_user_ids:
            placeholders = ",".join("?" * len(submitted_user_ids))
            cursor.execute(f"DELETE FROM users WHERE username != 'ADMINPNX' AND id NOT IN ({placeholders})", submitted_user_ids)
        else:
            cursor.execute("DELETE FROM users WHERE username != 'ADMINPNX'")

        conn.commit()
        conn.close()
        StorageAdapter.sync_database()
        return {"success": True}
    except Exception as e:
        print("Bulk update error:", e)
        try: conn.rollback(); conn.close()
        except: pass
        return {"success": False, "error": f"Employee ID already exists."}
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
