from fastapi import APIRouter, Request, Form, status, Response, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import os
import shutil
import time
from backend.core.database import (
    get_db, check_pessimistic_config_lock, get_model_statuses, sanitize_folder_name
)
from backend.core.security import get_current_user
from backend.core.config import V00_TEMPLATES_PATH, MP_READINESS_DATA_PATH
from backend.core.storage_adapter import StorageAdapter

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

# Trả về trạng thái thời gian cập nhật để Client theo dõi
@router.get("/api/config_status")
async def api_get_config_status():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_updated_at FROM app_config WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return {"config_updated_at": row[0] if row else 0}

# Bật khóa sửa Model Config
@router.post("/api/config/lock")
async def api_config_lock(request: Request):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=403)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 1")
    row = cursor.fetchone()
    current_time = int(time.time())
    
    if row and row['last_updated_by'] and row['last_updated_by'] != user['fullname'] and current_time - (row['config_updated_at'] or 0) < 600:
        conn.close()
        return {"success": False, "error": f"{row['last_updated_by']} đang chỉnh sửa Model Config, bạn không thể thao tác vào lúc này."}
        
    cursor.execute("UPDATE app_config SET config_updated_at = ?, last_updated_by = ? WHERE id = 1", (current_time, user['fullname']))
    conn.commit()
    conn.close()
    return {"success": True, "locked_at": current_time}

# Giải phóng khóa sửa Model Config
@router.post("/api/config/unlock")
async def api_config_unlock(request: Request):
    user = get_current_user(request)
    if not user:
        return Response(status_code=403)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT last_updated_by FROM app_config WHERE id = 1")
    row = cursor.fetchone()
    if row and row['last_updated_by'] == user['fullname']:
        cursor.execute("UPDATE app_config SET last_updated_by = NULL, config_updated_at = 0 WHERE id = 1")
        conn.commit()
    conn.close()
    return {"success": True}

# Render trang Cài đặt hệ thống (model_config.html)
@router.get("/setting")
async def get_setting(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    
    can_edit = (user["access_role"] == "Admin" or user["team"] == "Process DEV")
    locked_by = ""
    locked_at = 0
    if can_edit:
        cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 1")
        row = cursor.fetchone()
        current_time = int(time.time())
        if row and row['last_updated_by'] and current_time - (row['config_updated_at'] or 0) < 600:
            locked_by = row['last_updated_by']
            locked_at = row['config_updated_at']
    
    cursor.execute("SELECT * FROM models ORDER BY sort_order ASC, id ASC")
    models = [dict(m) for m in cursor.fetchall()]
    
    stats = get_model_statuses(cursor)
    for m in models:
        m['status_percent'] = stats.get(m['id'], "0.0%")
    
    cursor.execute("""
        SELECT m.* 
        FROM master_checklist m
        LEFT JOIN teams t ON m.team = t.name
        ORDER BY t.id ASC, m.level_1 ASC, m.level_2 ASC, m.id ASC
    """)
    master_checklist = [dict(m) for m in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM teams")
    teams = [dict(t) for t in cursor.fetchall()]
    
    conn.close()
    
    return templates.TemplateResponse(request=request, name="model_config.html", context={
        "current_user": dict(user),
        "models": models,
        "master_checklist": master_checklist,
        "teams": teams,
        "locked_by": locked_by,
        "locked_at": locked_at,
        "server_time": int(time.time()),
        "can_edit_backend": can_edit
    })

# Thêm mới hoặc cập nhật Model
@router.post("/api/models")
async def api_save_model(request: Request, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_config_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
    
    try:
        if data.get("id"):
            cursor.execute("""
                UPDATE models SET 
                name=?, model_type=?, customer=?, line=?, mp1st_date=?, mp1st_qty=?, 
                ship1st_date=?, ship1st_qty=?, status=?, activate=?, sort_order=?
                WHERE id=?
            """, (data.get("name"), data.get("model_type"), data.get("customer"), data.get("line"),
                  data.get("mp1st_date"), data.get("mp1st_qty") or 0, 
                  data.get("ship1st_date"), data.get("ship1st_qty") or 0, 
                  data.get("status"), data.get("activate"), data.get("sort_order") or 0, data.get("id")))
            model_id = data.get("id")
        else:
            cursor.execute("""
                INSERT INTO models (name, model_type, customer, line, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, status, activate, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("name"), data.get("model_type"), data.get("customer"), data.get("line"),
                  data.get("mp1st_date"), data.get("mp1st_qty") or 0, 
                  data.get("ship1st_date"), data.get("ship1st_qty") or 0, 
                  data.get("status"), data.get("activate"), data.get("sort_order") or 0))
            model_id = cursor.lastrowid
            
        conn.commit()
        cursor.execute("SELECT name FROM models")
        active_models = [r[0] for r in cursor.fetchall() if r[0]]
        StorageAdapter.reconcile_model_folders(active_models, background_tasks)
        StorageAdapter.sync_database(background_tasks)
    except Exception as e:
        conn.close()
        return {"error": str(e)}
        
    conn.close()
    return {"success": True, "id": model_id}

# Xóa một Model
@router.delete("/api/models/{model_id}")
async def api_delete_model(request: Request, model_id: int, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_config_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
    
    cursor.execute("SELECT name FROM models WHERE id=?", (model_id,))
    model_row = cursor.fetchone()
    if model_row:
        model_name = model_row[0]
        StorageAdapter.delete_model_folder(model_name, background_tasks)
        
    cursor.execute("DELETE FROM document_versions WHERE model_checklist_id IN (SELECT id FROM model_checklist WHERE model_id=?)", (model_id,))
    cursor.execute("DELETE FROM models WHERE id=?", (model_id,))
    cursor.execute("DELETE FROM model_checklist WHERE model_id=?", (model_id,))
    conn.commit()
    StorageAdapter.sync_database(background_tasks)
    conn.close()
    return {"success": True}

# Cập nhật Master Checklist
@router.post("/api/master_checklist")
async def api_save_master(request: Request):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_config_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
    
    try:
        old_path = None
        if data.get("id"):
            cursor.execute("SELECT team, level_1, level_2 FROM master_checklist WHERE id=?", (data.get("id"),))
            old_row = cursor.fetchone()
            if old_row:
                old_team = "".join(c if c.isalnum() else "_" for c in old_row[0])
                old_l1 = "".join(c if c.isalnum() else "_" for c in old_row[1])
                old_l2 = "".join(c if c.isalnum() else "_" for c in old_row[2])
                old_path = os.path.join(V00_TEMPLATES_PATH, old_team, old_l1, old_l2, "V00").replace("\\", "/")
                
            cursor.execute("UPDATE master_checklist SET team=?, level_1=?, level_2=? WHERE id=?", 
                           (data.get("team"), data.get("level_1"), data.get("level_2"), data.get("id")))
            item_id = data.get("id")
        else:
            cursor.execute("INSERT INTO master_checklist (team, level_1, level_2) VALUES (?, ?, ?)", 
                           (data.get("team"), data.get("level_1"), data.get("level_2")))
            item_id = cursor.lastrowid
        conn.commit()
        
        s_team = "".join(c if c.isalnum() else "_" for c in data.get("team", ""))
        s_l1 = "".join(c if c.isalnum() else "_" for c in data.get("level_1", ""))
        s_l2 = "".join(c if c.isalnum() else "_" for c in data.get("level_2", ""))
        new_path = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
        
        if old_path and old_path != new_path and os.path.exists(old_path):
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(old_path, new_path)
        else:
            os.makedirs(new_path, exist_ok=True)
            content_path = os.path.join(new_path, "content.html")
            if not os.path.exists(content_path):
                with open(content_path, "w", encoding="utf-8") as f:
                    f.write("")
                    
    except Exception as e:
        conn.close()
        return {"error": str(e)}
        
    conn.close()
    return {"success": True, "id": item_id}

# Xóa hạng mục khỏi Master Checklist
@router.delete("/api/master_checklist/{item_id}")
async def api_delete_master(request: Request, item_id: int):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_config_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
    cursor.execute("SELECT team, level_1, level_2 FROM master_checklist WHERE id=?", (item_id,))
    row = cursor.fetchone()
    
    cursor.execute("DELETE FROM master_checklist WHERE id=?", (item_id,))
    conn.commit()
    
    if row:
        s_team = "".join(c if c.isalnum() else "_" for c in row[0])
        s_l1 = "".join(c if c.isalnum() else "_" for c in row[1])
        s_l2 = "".join(c if c.isalnum() else "_" for c in row[2])
        path = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
        if os.path.exists(path):
            shutil.rmtree(path)
            
            l2_path = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2).replace("\\", "/")
            if os.path.exists(l2_path) and not os.listdir(l2_path):
                os.rmdir(l2_path)
                
            l1_path = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1).replace("\\", "/")
            if os.path.exists(l1_path) and not os.listdir(l1_path):
                os.rmdir(l1_path)
                
            team_path = os.path.join(V00_TEMPLATES_PATH, s_team).replace("\\", "/")
            if os.path.exists(team_path) and not os.listdir(team_path):
                os.rmdir(team_path)
    conn.close()
    return {"success": True}

# Lấy danh sách Checklist theo Model ID
@router.get("/api/model_checklist/{model_id}")
async def api_get_model_checklist(request: Request, model_id: int):
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.* 
        FROM model_checklist m
        LEFT JOIN teams t ON m.team = t.name
        WHERE m.model_id=? 
        ORDER BY t.id ASC, m.level_1 ASC, m.level_2 ASC, m.id ASC
    """, (model_id,))
    items = [dict(r) for r in cursor.fetchall()]
    
    user_team = user["team"] if user else None
    can_remark = False
    if user and (user["access_role"] == "Admin" or user_team == "Process DEV"):
        can_remark = True
    
    for item in items:
        item['role'] = 'Viewer'
        item['main_pic'] = ''
        item['can_remark'] = can_remark
        
        cursor.execute("""
            SELECT dv.id, dv.uploader_username, dv.status, u.fullname 
            FROM document_versions dv 
            LEFT JOIN users u ON dv.uploader_username = u.username 
            WHERE dv.model_checklist_id = ? 
            ORDER BY dv.id DESC LIMIT 1
        """, (item['id'],))
        latest_v = cursor.fetchone()
        
        item['doc_status'] = 'Pending'
        item['qa_status'] = 'Pending'
        
        if latest_v:
            if latest_v['fullname']:
                item['main_pic'] = latest_v['fullname']
            else:
                item['main_pic'] = latest_v['uploader_username'] or ''
                
            if latest_v['status'] in ('Pending', 'Approved', 'Rejected'):
                if latest_v['status'] != 'Rejected':
                    item['doc_status'] = 'Done'
                
                if latest_v['status'] == 'Approved':
                    item['qa_status'] = 'Approved'
                elif latest_v['status'] == 'Rejected':
                    item['qa_status'] = 'Rejected'
            
        if user_team and item['team'] == user_team:
            item['role'] = 'Uploader'
        elif user_team and latest_v:
            cursor.execute("SELECT id FROM confirmation_progress WHERE version_id = ? AND team_name = ?", (latest_v['id'], user_team))
            if cursor.fetchone():
                item['role'] = 'Approver'
                    
    conn.close()
    return items

# Lưu Remark cho hạng mục (Cơ chế Khóa Lạc Quan Optimistic)
@router.post("/api/model_checklist/{item_id}/remark")
async def api_save_checklist_remark(request: Request, item_id: int):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    remark = data.get("remark", "")
    client_updated_at = data.get("updated_at")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT updated_at FROM model_checklist WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Item not found"}
        
    db_updated_at = row[0]
    
    if client_updated_at and db_updated_at and client_updated_at != db_updated_at:
        conn.close()
        return {"success": False, "error": "Dữ liệu đã bị người khác sửa đổi. Nhấn OK hoặc F5 để update!"}
    
    new_updated_at = str(int(time.time()))
    
    cursor.execute("UPDATE model_checklist SET remark = ?, updated_at = ? WHERE id = ?", (remark, new_updated_at, item_id))
    conn.commit()
    from backend.core.gdrive_storage import sync_database_to_gdrive
    sync_database_to_gdrive()
    conn.close()
    return {"success": True, "updated_at": new_updated_at}

# Gán hạng mục Master vào Checklist của Model
@router.post("/api/model_checklist/{model_id}")
async def api_add_to_model_checklist(request: Request, model_id: int):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    conn = get_db()
    cursor = conn.cursor()
    err = check_pessimistic_config_lock(cursor, user)
    if err:
        conn.close()
        return {"success": False, "error": err}
    
    try:
        cursor.execute("SELECT name FROM models WHERE id = ?", (model_id,))
        model_row = cursor.fetchone()
        model_name = model_row[0] if model_row else None

        for item in data.get("items", []):
            team = item.get("team")
            level_1 = item.get("level_1")
            level_2 = item.get("level_2")
            cursor.execute("SELECT id FROM model_checklist WHERE model_id=? AND team=? AND level_1=? AND level_2=?", 
                          (model_id, team, level_1, level_2))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO model_checklist (model_id, team, level_1, level_2) VALUES (?, ?, ?, ?)",
                               (model_id, team, level_1, level_2))
            if model_name:
                s_model = sanitize_folder_name(model_name)
                s_team = sanitize_folder_name(team)
                s_l1 = sanitize_folder_name(level_1)
                s_l2 = sanitize_folder_name(level_2)
                path = os.path.join(MP_READINESS_DATA_PATH, s_model, s_team, s_l1, s_l2).replace("\\", "/")
                os.makedirs(path, exist_ok=True)
        conn.commit()
        from backend.core.gdrive_storage import sync_database_to_gdrive
        sync_database_to_gdrive()
    except Exception as e:
        conn.close()
        return {"error": str(e)}
        
    conn.close()
    return {"success": True}

# Bỏ gán một hạng mục khỏi Checklist Model
@router.post("/api/model_checklist/{model_id}/remove")
async def api_remove_from_model_checklist(request: Request, model_id: int):
    user = get_current_user(request)
    if not user or (user["access_role"] != "Admin" and user["team"] != "Process DEV"):
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    item_ids = data.get("item_ids", [])
    if not item_ids:
        return {"success": True}
        
    conn = get_db()
    cursor = conn.cursor()
    
    placeholders = ",".join("?" * len(item_ids))
    cursor.execute(f"DELETE FROM document_versions WHERE model_checklist_id IN (SELECT id FROM model_checklist WHERE model_id=? AND id IN ({placeholders}))", [model_id] + item_ids)
    cursor.execute(f"DELETE FROM model_checklist WHERE model_id=? AND id IN ({placeholders})", [model_id] + item_ids)
    conn.commit()
    from backend.core.gdrive_storage import sync_database_to_gdrive
    sync_database_to_gdrive()
    conn.close()
    
    return {"success": True}
