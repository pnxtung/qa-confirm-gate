from fastapi import APIRouter, Request, Response, status, File, UploadFile, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from backend.core.storage_adapter import StorageAdapter
import sqlite3
import os
import shutil
from typing import List
import time
from datetime import datetime

from backend.core.database import (
    get_db, sanitize_folder_name, get_version_dir_from_checklist, get_version_dir, check_pessimistic_lock
)
from backend.core.security import get_current_user
from backend.core.config import V00_TEMPLATES_PATH

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

MAX_VERSION_SIZE_BYTES = 40 * 1024 * 1024  # 40 MB

def get_version_total_size(version_id: str, new_html_content: str = None, new_files_bytes: int = 0) -> int:
    total = new_files_bytes
    if new_html_content is not None:
        total += len(new_html_content.encode('utf-8'))
        
    if not version_id.startswith("V00_"):
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(file_size) FROM document_files WHERE version_id = ?", (int(version_id),))
            row = cursor.fetchone()
            if row and row[0]:
                total += row[0]
        finally:
            conn.close()
            
    return total

# Render giao diện trang Upload
@router.get("/upload")
async def get_upload_empty(request: Request, model_id: int = None):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM teams ORDER BY name")
    active_teams = [dict(r) for r in cursor.fetchall()]
    
    model_name = None
    allowed_items = []
    if model_id:
        cursor.execute("SELECT name FROM models WHERE id = ?", (model_id,))
        m_row = cursor.fetchone()
        if m_row:
            model_name = m_row["name"]
            
        cursor.execute("SELECT * FROM model_checklist WHERE model_id = ?", (model_id,))
        allowed_items = [dict(r) for r in cursor.fetchall()]
        
        for ai in allowed_items:
            if user["team"] == ai["team"]:
                ai["role_type"] = "upload"
            else:
                cursor.execute("""
                    SELECT 1 FROM document_versions dv
                    JOIN confirmation_progress cp ON dv.id = cp.version_id
                    WHERE dv.model_checklist_id = ? 
                      AND dv.status = 'Pending' 
                      AND cp.team_name = ? 
                      AND cp.status = 'Waiting'
                    ORDER BY dv.id DESC LIMIT 1
                """, (ai["id"], user["team"]))
                if cursor.fetchone():
                    ai["role_type"] = "approval"
                else:
                    ai["role_type"] = "readonly"
        
    response = templates.TemplateResponse(request=request, name="upload_document.html", context={
        "current_user": dict(user),
        "checklist_item": None,
        "active_teams": active_teams,
        "model_name": model_name,
        "allowed_items": allowed_items
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    conn.close()
    return response

# Render trang Upload cụ thể cho một tài liệu (Checklist item)
@router.get("/upload/{model_checklist_id}")
async def get_upload(request: Request, model_checklist_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mc.*, m.name as model_name 
        FROM model_checklist mc 
        LEFT JOIN models m ON mc.model_id = m.id 
        WHERE mc.id = ?
    """, (model_checklist_id,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return RedirectResponse(url="/upload?invalid_id=true", status_code=status.HTTP_302_FOUND)
        
    model_name = item["model_name"]
    model_id = item["model_id"]
    
    cursor.execute("SELECT * FROM model_checklist WHERE model_id = ?", (model_id,))
    allowed_items = [dict(r) for r in cursor.fetchall()]
    
    for ai in allowed_items:
        if user["team"] == ai["team"]:
            ai["role_type"] = "upload"
        else:
            cursor.execute("""
                SELECT 1 FROM document_versions dv
                JOIN confirmation_progress cp ON dv.id = cp.version_id
                WHERE dv.model_checklist_id = ? 
                  AND dv.status = 'Pending' 
                  AND cp.team_name = ? 
                  AND cp.status = 'Waiting'
                ORDER BY dv.id DESC LIMIT 1
            """, (ai["id"], user["team"]))
            if cursor.fetchone():
                ai["role_type"] = "approval"
            else:
                ai["role_type"] = "readonly"
    
    cursor.execute("SELECT * FROM teams WHERE active = 'Yes'")
    active_teams = [dict(t) for t in cursor.fetchall()]
    response = templates.TemplateResponse(request=request, name="upload_document.html", context={
        "current_user": dict(user),
        "checklist_item": dict(item),
        "active_teams": active_teams,
        "model_name": model_name,
        "allowed_items": allowed_items
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    conn.close()
    return response

@router.get("/api/documents/{model_checklist_id}")
def api_get_documents(request: Request, model_checklist_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT dv.*, u.fullname as uploader_fullname, u.team as uploader_team,
                   mc.team, mc.level_1, mc.level_2, m.name as model_name
            FROM document_versions dv 
            LEFT JOIN users u ON dv.uploader_username = u.username 
            JOIN model_checklist mc ON dv.model_checklist_id = mc.id
            LEFT JOIN models m ON mc.model_id = m.id
            WHERE dv.model_checklist_id = ? 
            ORDER BY dv.id DESC
        """, (model_checklist_id,))
        versions = [dict(v) for v in cursor.fetchall()]
        
        for v in versions:
            model_name = v.get('model_name') or "Unknown"
            v['content'] = StorageAdapter.read_document_html(model_name, v['team'], v['level_1'], v['level_2'], v['version_no'])
                    
            cursor.execute("SELECT * FROM confirmation_progress WHERE version_id = ? ORDER BY step_order ASC", (v['id'],))
            v['progress'] = [dict(p) for p in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM document_files WHERE version_id = ? ORDER BY id ASC", (v['id'],))
            db_files = [dict(f) for f in cursor.fetchall()]
            for f in db_files:
                f['size'] = f.get('file_size') or 0
            v['files'] = db_files
            
        cursor.execute("""
            SELECT mc.team, mc.level_1, mc.level_2, m.name as model_name
            FROM model_checklist mc
            LEFT JOIN models m ON mc.model_id = m.id
            WHERE mc.id = ?
        """, (model_checklist_id,))
        item = cursor.fetchone()
        if item:
            model_name = item['model_name'] or "Template"
            v00_content = StorageAdapter.read_document_html(model_name, item['team'], item['level_1'], item['level_2'], "V00")
            
            # Always append V00 template entry
            versions.append({
                "id": f"V00_{model_checklist_id}",
                "version_no": "V00",
                "uploader_username": "Admin",
                "uploader_fullname": "System",
                "status": "Template",
                "content": v00_content or "",
                "progress": [],
                "files": []
            })
    finally:
        conn.close()

    return JSONResponse(
        content=versions,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

# Khóa Document khi User ấn Edit
@router.post("/api/documents/{checklist_id}/lock")
async def api_lock_document(request: Request, checklist_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT locked_by, locked_at FROM model_checklist WHERE id = ?", (checklist_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Tài liệu không tồn tại."}
        
    locked_by = row[0]
    locked_at = row[1]
    now = int(time.time())
    username = user['fullname'] + ' (' + user['username'] + ')'
    
    if locked_by and locked_by != username:
        if locked_at:
            if now - int(locked_at) < 1800:
                conn.close()
                return {"success": False, "error": f"{locked_by} đang chỉnh sửa, bạn không thể thao tác vào lúc này."}
                
    cursor.execute("UPDATE model_checklist SET locked_by = ?, locked_at = ? WHERE id = ?", (username, str(now), checklist_id))
    conn.commit()
    conn.close()
    return {"success": True}

# Giải phóng khóa cho Document
@router.post("/api/documents/{checklist_id}/unlock")
async def api_unlock_document(request: Request, checklist_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    username = user['fullname'] + ' (' + user['username'] + ')'
    
    if user['access_role'] == 'Admin':
        cursor.execute("UPDATE model_checklist SET locked_by = NULL, locked_at = NULL WHERE id = ?", (checklist_id,))
    else:
        cursor.execute("UPDATE model_checklist SET locked_by = NULL, locked_at = NULL WHERE id = ? AND locked_by = ?", (checklist_id, username))
        
    conn.commit()
    conn.close()
    return {"success": True}

@router.post("/api/documents/{model_checklist_id}/version")
def api_create_version(request: Request, model_checklist_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            return Response(status_code=status.HTTP_403_FORBIDDEN)
            
        lock_err = check_pessimistic_lock(cursor, model_checklist_id, user)
        if lock_err:
            return {"success": False, "error": lock_err}
        
        cursor.execute("SELECT count(id) FROM document_versions WHERE model_checklist_id = ?", (model_checklist_id,))
        count = cursor.fetchone()[0]
        next_ver = f"V{count + 1:02d}"
        
        cursor.execute("""
            SELECT dv.id, dv.version_no, mc.team, mc.level_1, mc.level_2, m.name as model_name
            FROM document_versions dv
            JOIN model_checklist mc ON dv.model_checklist_id = mc.id
            LEFT JOIN models m ON mc.model_id = m.id
            WHERE dv.model_checklist_id = ? 
            ORDER BY dv.id DESC LIMIT 1
        """, (model_checklist_id,))
        latest_v = cursor.fetchone()
        
        if not latest_v:
            cursor.execute("""
                SELECT mc.team, mc.level_1, mc.level_2, m.name as model_name
                FROM model_checklist mc
                LEFT JOIN models m ON mc.model_id = m.id
                WHERE mc.id = ?
            """, (model_checklist_id,))
            meta_item = cursor.fetchone()
            model_name = meta_item['model_name'] if meta_item else "Unknown"
            team = meta_item['team'] if meta_item else "Unknown"
            level_1 = meta_item['level_1'] if meta_item else "Unknown"
            level_2 = meta_item['level_2'] if meta_item else "Unknown"
        else:
            model_name = latest_v['model_name'] or "Unknown"
            team = latest_v['team']
            level_1 = latest_v['level_1']
            level_2 = latest_v['level_2']
        
        cursor.execute("""
            INSERT INTO document_versions (model_checklist_id, version_no, content, uploader_username, status) 
            VALUES (?, ?, ?, ?, 'Draft')
        """, (model_checklist_id, next_ver, "", user["username"]))
        new_version_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO confirmation_progress (version_id, step_order, team_name) 
            VALUES (?, ?, 'OQA')
        """, (new_version_id, 1))
        
        if latest_v:
            latest_version_id = latest_v["id"]
            cursor.execute("SELECT filename, filepath, file_size FROM document_files WHERE version_id = ?", (latest_version_id,))
            files_to_copy = cursor.fetchall()
            for f in files_to_copy:
                old_filepath = f["filepath"]
                new_filepath = StorageAdapter.get_supabase_file_path(model_name, team, level_1, level_2, next_ver, f["filename"])
                if old_filepath:
                    StorageAdapter.copy_file(old_filepath, new_filepath)
                cursor.execute("""
                    INSERT INTO document_files (version_id, filename, filepath, file_size, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (new_version_id, f["filename"], new_filepath, f.get("file_size", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Copy content.html
            old_html_path = StorageAdapter.get_supabase_html_path(model_name, team, level_1, level_2, latest_v["version_no"])
            new_html_path = StorageAdapter.get_supabase_html_path(model_name, team, level_1, level_2, next_ver)
            StorageAdapter.copy_file(old_html_path, new_html_path)
        else:
            # Copy V00 content.html if exists
            v00_html_path = StorageAdapter.get_supabase_html_path(model_name, team, level_1, level_2, "V00")
            new_html_path = StorageAdapter.get_supabase_html_path(model_name, team, level_1, level_2, next_ver)
            StorageAdapter.copy_file(v00_html_path, new_html_path)

        conn.commit()
        return {"success": True, "version_id": new_version_id, "version_no": next_ver}
    finally:
        conn.close()

# Chuyển trạng thái từ Nháp sang Pending (Hoàn thành Upload)
@router.post("/api/documents/version/{version_id}/submit")
async def api_submit_version(request: Request, version_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (version_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Phiên bản không tồn tại."}
    checklist_id = row[0]
    
    cursor.execute("SELECT locked_by, locked_at FROM model_checklist WHERE id = ?", (checklist_id,))
    lock_row = cursor.fetchone()
    if lock_row:
        locked_by, locked_at = lock_row[0], lock_row[1]
        username = user['fullname'] + ' (' + user['username'] + ')'
        if locked_by and locked_by != username:
            if locked_at and int(time.time()) - int(locked_at) < 1800:
                conn.close()
                return {"success": False, "error": f"{locked_by} đang chỉnh sửa, bạn không thể thao tác vào lúc này."}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE document_versions SET status = 'Pending', uploaded_at = ? WHERE id = ?", (now_str, version_id))
    conn.commit()
    from backend.core.storage_adapter import StorageAdapter
    StorageAdapter.sync_database()
    conn.close()
    return {"success": True}

# Hủy Submit, khôi phục Version về Draft (Dành cho Admin)
@router.post("/api/documents/version/{version_id}/cancel_upload")
async def api_cancel_upload(request: Request, version_id: int):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (version_id,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Version not found"}
        checklist_id = row[0]
        
        cursor.execute("SELECT locked_by, locked_at FROM model_checklist WHERE id = ?", (checklist_id,))
        lock_row = cursor.fetchone()
        if lock_row:
            locked_by, locked_at = lock_row[0], lock_row[1]
            username = user['fullname'] + ' (' + user['username'] + ')'
            if locked_by and locked_by != username:
                if locked_at and int(time.time()) - int(locked_at) < 1800:
                    return {"success": False, "error": f"{locked_by} đang chỉnh sửa, bạn không thể thao tác vào lúc này."}

        cursor.execute("SELECT id FROM document_versions WHERE model_checklist_id = ? ORDER BY id DESC LIMIT 1", (checklist_id,))
        latest_row = cursor.fetchone()
        if latest_row and latest_row[0] != version_id:
            return {"success": False, "error": "Cannot cancel upload. A newer version already exists."}

        cursor.execute("""
            UPDATE document_versions 
            SET status = 'Draft', uploaded_at = NULL, completed_at = NULL 
            WHERE id = ?
        """, (version_id,))
        
        cursor.execute("""
            UPDATE confirmation_progress 
            SET status = 'Pending', action_by = NULL, comment = '', action_at = NULL 
            WHERE version_id = ?
        """, (version_id,))
        
        conn.commit()
        from backend.core.storage_adapter import StorageAdapter
        StorageAdapter.sync_database()
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
        
    return {"success": True}

# Xóa bản ghi Version Nháp hoàn toàn (Chỉ Admin)
@router.delete("/api/documents/version/{version_id}")
async def api_delete_version(request: Request, version_id: int):
    user = get_current_user(request)
    if not user or user["access_role"] != "Admin":
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (version_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Phiên bản không tồn tại."}
    checklist_id = row[0]
    
    cursor.execute("SELECT locked_by, locked_at FROM model_checklist WHERE id = ?", (checklist_id,))
    lock_row = cursor.fetchone()
    if lock_row:
        locked_by, locked_at = lock_row[0], lock_row[1]
        username = user['fullname'] + ' (' + user['username'] + ')'
        if locked_by and locked_by != username:
            if locked_at and int(time.time()) - int(locked_at) < 1800:
                conn.close()
                return {"success": False, "error": f"{locked_by} đang chỉnh sửa, bạn không thể thao tác vào lúc này."}

    v_dir = get_version_dir(version_id)
    
    cursor.execute("DELETE FROM document_files WHERE version_id = ?", (version_id,))
    cursor.execute("DELETE FROM confirmation_progress WHERE version_id = ?", (version_id,))
    cursor.execute("DELETE FROM document_versions WHERE id = ?", (version_id,))
    
    conn.commit()
    from backend.core.storage_adapter import StorageAdapter
    StorageAdapter.sync_database()
    conn.close()
    
    if v_dir and os.path.exists(v_dir):
        shutil.rmtree(v_dir, ignore_errors=True)
        
    return {"success": True}

# Cập nhật thứ tự các phòng ban Ký Duyệt
@router.post("/api/documents/version/{version_id}/progress")
async def api_save_progress(request: Request, version_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    steps = data.get("steps", [])
    
    if not any(s.get('team_name') == 'OQA' for s in steps):
        return {"success": False, "error": "OQA team is required!"}
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (version_id,))
    row = cursor.fetchone()
    if row:
        lock_err = check_pessimistic_lock(cursor, row[0], user)
        if lock_err:
            conn.close()
            return {"success": False, "error": lock_err}
    
    cursor.execute("DELETE FROM confirmation_progress WHERE version_id = ?", (version_id,))
    
    for idx, step in enumerate(steps):
        cursor.execute("""
            INSERT INTO confirmation_progress (version_id, step_order, team_name, status, comment, action_by, action_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version_id, idx + 1, step.get('team_name'), step.get('status', 'Waiting'), step.get('comment'), step.get('action_by'), step.get('action_at')))
        
    conn.commit()
    conn.close()
    return {"success": True}

# Xác nhận Duyệt / Từ chối
@router.post("/api/documents/progress/{progress_id}/approve")
async def api_approve_progress(request: Request, progress_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    new_status = data.get("status")
    comment = data.get("comment", "")
    
    conn = get_db()
    cursor = conn.cursor()
    
    now_str = datetime.now().strftime("%H:%M:%S %m/%d/%Y")
    
    cursor.execute("SELECT version_id, status FROM confirmation_progress WHERE id = ?", (progress_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "Tài liệu đã bị thay đổi trạng thái bởi người khác. Vui lòng bấm F5 để tải lại trang."}
        
    version_id = row[0]
    progress_status = row[1]
    
    cursor.execute("SELECT status FROM document_versions WHERE id = ?", (version_id,))
    doc_row = cursor.fetchone()
    if doc_row and doc_row[0] != 'Pending':
        conn.close()
        return {"success": False, "error": "Tài liệu đã bị thay đổi trạng thái bởi người khác. Vui lòng bấm F5 để tải lại trang."}
        
    if progress_status not in ('Pending', 'Waiting'):
        conn.close()
        return {"success": False, "error": "Tài liệu đã bị thay đổi trạng thái bởi người khác. Vui lòng bấm F5 để tải lại trang."}
    
    cursor.execute("""
        UPDATE confirmation_progress 
        SET status = ?, comment = ?, action_by = ?, action_at = ?
        WHERE id = ?
    """, (new_status, comment, user['fullname'], now_str, progress_id))
    
    cursor.execute("SELECT version_id FROM confirmation_progress WHERE id = ?", (progress_id,))
    v_row = cursor.fetchone()
    if v_row:
        v_id = v_row[0]
        cursor.execute("SELECT status FROM confirmation_progress WHERE version_id = ?", (v_id,))
        all_statuses = [r[0] for r in cursor.fetchall()]
        
        v_status = 'Pending'
        if 'Rejected' in all_statuses:
            v_status = 'Rejected'
        elif all(s == 'Approved' for s in all_statuses):
            v_status = 'Approved'
            
        if v_status != 'Pending':
            cursor.execute("UPDATE document_versions SET status = ?, completed_at = ? WHERE id = ?", (v_status, now_str, v_id))
    
    conn.commit()
    conn.close()
    return {"success": True}

# Ghi nội dung HTML trình soạn thảo ra kho lưu trữ (StorageAdapter & BackgroundTasks)
@router.post("/api/documents/version/{version_id}/content")
async def api_save_content(request: Request, version_id: str, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    data = await request.json()
    html_content = data.get("content", "")
    
    conn = get_db()
    cursor = conn.cursor()
    
    if version_id.startswith("V00_"):
        if user["access_role"] != "Admin" and user["team"] != "Process DEV":
            conn.close()
            return Response(status_code=status.HTTP_403_FORBIDDEN)
        
        model_checklist_id = int(version_id.split("_")[1])
        lock_err = check_pessimistic_lock(cursor, model_checklist_id, user)
        if lock_err:
            conn.close()
            return {"success": False, "error": lock_err}
        cursor.execute("""
            SELECT m.name as model_name, mc.team, mc.level_1, mc.level_2 
            FROM model_checklist mc 
            LEFT JOIN models m ON mc.model_id = m.id 
            WHERE mc.id = ?
        """, (model_checklist_id,))
        item = cursor.fetchone()
        if not item:
            conn.close()
            return {"success": False, "error": "Template not found"}
        model_name = item['model_name'] or "Template"
        team = item['team']
        level_1 = item['level_1']
        level_2 = item['level_2']
        version_no = "V00"
    else:
        version_id_int = int(version_id)
        cursor.execute("""
            SELECT dv.model_checklist_id, dv.version_no, mc.team, mc.level_1, mc.level_2, m.name as model_name
            FROM document_versions dv
            JOIN model_checklist mc ON dv.model_checklist_id = mc.id
            LEFT JOIN models m ON mc.model_id = m.id
            WHERE dv.id = ?
        """, (version_id_int,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "Version not found"}
            
        checklist_id = row['model_checklist_id']
        lock_err = check_pessimistic_lock(cursor, checklist_id, user)
        if lock_err:
            conn.close()
            return {"success": False, "error": lock_err}
            
        model_name = row['model_name'] or "Unknown"
        team = row['team']
        level_1 = row['level_1']
        level_2 = row['level_2']
        version_no = row['version_no']
        
        cursor.execute("UPDATE document_versions SET uploader_username = ? WHERE id = ?", (user['username'], version_id_int))
        conn.commit()
    conn.close()

    # Check 40MB limit before saving
    total_size = get_version_total_size(version_id, new_html_content=html_content)
    if total_size > MAX_VERSION_SIZE_BYTES:
        return {"success": False, "error": "Không thể lưu do tổng dung lượng version vượt quá 40MB!"}

    # Save HTML using unified StorageAdapter with Async BackgroundTasks
    StorageAdapter.save_document_html(model_name, team, level_1, level_2, version_no, html_content, background_tasks)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE document_versions SET content = ? WHERE id = ?", ("", version_id))
    conn.commit()
    conn.close()

    # Trigger DB sync (local / gdrive / supabase)
    StorageAdapter.sync_database(background_tasks)
    
    return {"success": True}

# Upload files đính kèm
@router.post("/api/documents/version/{version_id}/files")
async def api_upload_files(request: Request, version_id: str, files: List[UploadFile] = File(...)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            return Response(status_code=status.HTTP_403_FORBIDDEN)
            
        is_v00 = version_id.startswith("V00_")
        if is_v00:
            if user["access_role"] != "Admin" and user["team"] != "Process DEV":
                return Response(status_code=status.HTTP_403_FORBIDDEN)
            model_checklist_id = int(version_id.split("_")[1])
            version_id_int = None
            version_no = "V00"
            cursor.execute("""
                SELECT mc.team, mc.level_1, mc.level_2, m.name as model_name
                FROM model_checklist mc
                LEFT JOIN models m ON mc.model_id = m.id
                WHERE mc.id = ?
            """, (model_checklist_id,))
            v_row = cursor.fetchone()
            if not v_row:
                return Response(status_code=404)
            model_name = v_row['model_name'] or "Template"
            team = v_row['team']
            level_1 = v_row['level_1']
            level_2 = v_row['level_2']
            checklist_id = model_checklist_id
        else:
            version_id_int = int(version_id)
            cursor.execute("""
                SELECT dv.model_checklist_id, dv.version_no, mc.team, mc.level_1, mc.level_2, m.name as model_name
                FROM document_versions dv
                JOIN model_checklist mc ON dv.model_checklist_id = mc.id
                LEFT JOIN models m ON mc.model_id = m.id
                WHERE dv.id = ?
            """, (version_id_int,))
            v_row = cursor.fetchone()
            if not v_row:
                return Response(status_code=404)
            checklist_id = v_row['model_checklist_id']
            version_no = v_row['version_no']
            model_name = v_row['model_name'] or "Unknown"
            team = v_row['team']
            level_1 = v_row['level_1']
            level_2 = v_row['level_2']

        if checklist_id:
            lock_err = check_pessimistic_lock(cursor, checklist_id, user)
            if lock_err:
                return {"success": False, "error": lock_err}
        
        # Calculate new files size and validate total version size
        new_files_bytes = 0
        file_contents = []
        for file in files:
            file_content = await file.read()
            file_contents.append(file_content)
            new_files_bytes += len(file_content)

        total_size = get_version_total_size(version_id, new_files_bytes=new_files_bytes)
        if total_size > MAX_VERSION_SIZE_BYTES:
            return {"success": False, "error": "Không thể lưu do tổng dung lượng version vượt quá 40MB!"}
        
        uploaded_records = []
        for file, content in zip(files, file_contents):
            safe_filename = sanitize_folder_name(file.filename)
            file_size = len(content)
            
            storage_path = StorageAdapter.get_supabase_file_path(model_name, team, level_1, level_2, version_no, safe_filename)
            StorageAdapter.upload_file_bytes(storage_path, content, content_type=file.content_type or "application/octet-stream")
                
            if not is_v00:
                cursor.execute("""
                    INSERT INTO document_files (version_id, filename, filepath, file_size, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (version_id_int, safe_filename, storage_path, file_size, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                uploaded_records.append({
                    "id": cursor.lastrowid,
                    "filename": safe_filename,
                    "filepath": storage_path,
                    "file_size": file_size
                })
            else:
                uploaded_records.append({
                    "id": f"V00_{model_checklist_id}_{safe_filename}",
                    "filename": safe_filename,
                    "file_path": storage_path,
                    "file_size": file_size
                })
                
        conn.commit()
        return {"success": True, "files": uploaded_records}
    finally:
        conn.close()

# Xóa 1 File đính kèm
@router.delete("/api/documents/version/files/{file_id}")
def api_delete_file(request: Request, file_id: str):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            return Response(status_code=status.HTTP_403_FORBIDDEN)
            
        if file_id.startswith("V00_"):
            if user["access_role"] != "Admin" and user["team"] != "Process DEV":
                return Response(status_code=status.HTTP_403_FORBIDDEN)
                
            parts = file_id.split("_", 2)
            if len(parts) == 3:
                model_checklist_id = int(parts[1])
                filename = parts[2]
                cursor.execute("""
                    SELECT mc.team, mc.level_1, mc.level_2, m.name as model_name 
                    FROM model_checklist mc 
                    LEFT JOIN models m ON mc.model_id = m.id
                    WHERE mc.id = ?
                """, (model_checklist_id,))
                item = cursor.fetchone()
                if item:
                    model_name = item['model_name'] or "Template"
                    storage_path = StorageAdapter.get_supabase_file_path(model_name, item['team'], item['level_1'], item['level_2'], "V00", filename)
                    StorageAdapter.delete_file(storage_path)
            return {"success": True}

        file_id_int = int(file_id)
        cursor.execute("SELECT filepath FROM document_files WHERE id = ?", (file_id_int,))
        f = cursor.fetchone()
        if not f:
            return Response(status_code=404)
            
        if f["filepath"]:
            StorageAdapter.delete_file(f["filepath"])
            
        cursor.execute("DELETE FROM document_files WHERE id = ?", (file_id_int,))
        conn.commit()
        return {"success": True}
    finally:
        conn.close()

# Hỗ trợ Client Download file
@router.get("/api/documents/version/files/{file_id}/download")
def api_download_file(request: Request, file_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT filepath, filename FROM document_files WHERE id = ?", (file_id,))
        f = cursor.fetchone()
    finally:
        conn.close()
        
    if not f or not f["filepath"]:
        return Response(status_code=404)
        
    file_bytes = StorageAdapter.download_file_bytes(f["filepath"])
    if not file_bytes:
        return Response(status_code=404)
        
    from fastapi.responses import StreamingResponse
    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{f["filename"]}"'}
    )
