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
    if version_id.startswith("V00_"):
        model_checklist_id = int(version_id.split("_")[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT team, level_1, level_2 FROM model_checklist WHERE id = ?", (model_checklist_id,))
        item = cursor.fetchone()
        conn.close()
        if not item:
            return new_files_bytes
        s_team = "".join(c if c.isalnum() else "_" for c in item['team'])
        s_l1 = "".join(c if c.isalnum() else "_" for c in item['level_1'])
        s_l2 = "".join(c if c.isalnum() else "_" for c in item['level_2'])
        v_dir = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
    else:
        v_dir = get_version_dir(int(version_id))

    if not v_dir or not os.path.exists(v_dir):
        return new_files_bytes

    total = new_files_bytes
    for fn in os.listdir(v_dir):
        fp = os.path.join(v_dir, fn)
        if os.path.isfile(fp):
            if fn == "content.html" and new_html_content is not None:
                total += len(new_html_content.encode('utf-8'))
            else:
                total += os.path.getsize(fp)

    if new_html_content is not None and not os.path.exists(os.path.join(v_dir, "content.html")):
        total += len(new_html_content.encode('utf-8'))

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

# Tải lịch sử tất cả Versions của một hạng mục
@router.get("/api/documents/{model_checklist_id}")
async def api_get_documents(request: Request, model_checklist_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT dv.*, u.fullname as uploader_fullname, u.team as uploader_team 
        FROM document_versions dv 
        LEFT JOIN users u ON dv.uploader_username = u.username 
        WHERE dv.model_checklist_id = ? 
        ORDER BY dv.id DESC
    """, (model_checklist_id,))
    versions = [dict(v) for v in cursor.fetchall()]
    
    for v in versions:
        v_dir = get_version_dir(v['id'])
        content_path = os.path.join(v_dir, "content.html") if v_dir else ""
        if os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                v['content'] = f.read()
                
        cursor.execute("SELECT * FROM confirmation_progress WHERE version_id = ? ORDER BY step_order ASC", (v['id'],))
        v['progress'] = [dict(p) for p in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM document_files WHERE version_id = ? ORDER BY id ASC", (v['id'],))
        db_files = [dict(f) for f in cursor.fetchall()]
        for f in db_files:
            fp = f.get('filepath')
            if fp and os.path.exists(fp):
                f['size'] = os.path.getsize(fp)
            else:
                f['size'] = 0
        v['files'] = db_files
        
    cursor.execute("""
        SELECT mc.team, mc.level_1, mc.level_2 
        FROM model_checklist mc
        WHERE mc.id = ?
    """, (model_checklist_id,))
    item = cursor.fetchone()
    if item:
        s_team = "".join(c if c.isalnum() else "_" for c in item['team'])
        s_l1 = "".join(c if c.isalnum() else "_" for c in item['level_1'])
        s_l2 = "".join(c if c.isalnum() else "_" for c in item['level_2'])
        v00_dir = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
        
        if os.path.exists(v00_dir):
            v00_content = ""
            content_path = os.path.join(v00_dir, "content.html")
            if os.path.exists(content_path):
                with open(content_path, "r", encoding="utf-8") as f:
                    v00_content = f.read()
            
            v00_files = []
            for fname in os.listdir(v00_dir):
                if fname != "content.html":
                    fp = os.path.join(v00_dir, fname)
                    v00_files.append({
                        "id": f"V00_{model_checklist_id}_{fname}",
                        "filename": fname,
                        "file_path": fp,
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0
                    })

            versions.append({
                "id": f"V00_{model_checklist_id}",
                "version_no": "V00",
                "uploader_username": "Admin",
                "uploader_fullname": "System",
                "status": "Template",
                "content": v00_content,
                "progress": [],
                "files": v00_files
            })
            
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

# Tạo Version Nháp mới (Clone từ bản cũ hoặc V00)
@router.post("/api/documents/{model_checklist_id}/version")
async def api_create_version(request: Request, model_checklist_id: int):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    lock_err = check_pessimistic_lock(cursor, model_checklist_id, user)
    if lock_err:
        conn.close()
        return {"success": False, "error": lock_err}
    
    cursor.execute("SELECT count(id) FROM document_versions WHERE model_checklist_id = ?", (model_checklist_id,))
    count = cursor.fetchone()[0]
    next_ver = f"V{count + 1:02d}"
    
    cursor.execute("SELECT id FROM document_versions WHERE model_checklist_id = ? ORDER BY id DESC LIMIT 1", (model_checklist_id,))
    latest_v = cursor.fetchone()
    
    cursor.execute("""
        INSERT INTO document_versions (model_checklist_id, version_no, content, uploader_username, status) 
        VALUES (?, ?, ?, ?, 'Draft')
    """, (model_checklist_id, next_ver, "", user["username"]))
    new_version_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO confirmation_progress (version_id, step_order, team_name) 
        VALUES (?, ?, 'OQA')
    """, (new_version_id, 1))
    
    dest_dir = get_version_dir_from_checklist(model_checklist_id, next_ver)
    
    if latest_v:
        latest_version_id = latest_v["id"]
        src_dir = get_version_dir(latest_version_id)
        
        if src_dir and os.path.exists(src_dir):
            shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
                    
        cursor.execute("SELECT filename, filepath FROM document_files WHERE version_id = ?", (latest_version_id,))
        files_to_copy = cursor.fetchall()
        for f in files_to_copy:
            old_filepath = f["filepath"]
            if src_dir and dest_dir:
                new_filepath = old_filepath.replace(src_dir, dest_dir)
            else:
                new_filepath = old_filepath
            cursor.execute("""
                INSERT INTO document_files (version_id, filename, filepath, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (new_version_id, f["filename"], new_filepath, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        cursor.execute("SELECT team, level_1, level_2 FROM model_checklist WHERE id = ?", (model_checklist_id,))
        item = cursor.fetchone()
        cloned_from_v00 = False
        if item:
            s_team = "".join(c if c.isalnum() else "_" for c in item['team'])
            s_l1 = "".join(c if c.isalnum() else "_" for c in item['level_1'])
            s_l2 = "".join(c if c.isalnum() else "_" for c in item['level_2'])
            v00_dir = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
            if os.path.exists(v00_dir):
                shutil.copytree(v00_dir, dest_dir, dirs_exist_ok=True)
                for fname in os.listdir(v00_dir):
                    if fname != "content.html":
                        new_filepath = os.path.join(dest_dir, fname)
                        cursor.execute("""
                            INSERT INTO document_files (version_id, filename, filepath, uploaded_at)
                            VALUES (?, ?, ?, ?)
                        """, (new_version_id, fname, new_filepath, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                cloned_from_v00 = True
                
        if not cloned_from_v00:
            os.makedirs(dest_dir, exist_ok=True)
            with open(os.path.join(dest_dir, "content.html"), "w", encoding="utf-8") as f:
                f.write("")

    conn.commit()
    StorageAdapter.sync_database()
    conn.close()
    
    return {"success": True, "version_id": new_version_id, "version_no": next_ver}

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
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    if version_id.startswith("V00_"):
        checklist_id = int(version_id.split("_")[1])
    else:
        cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (int(version_id),))
        row = cursor.fetchone()
        checklist_id = row[0] if row else None

    if checklist_id:
        lock_err = check_pessimistic_lock(cursor, checklist_id, user)
        if lock_err:
            conn.close()
            return {"success": False, "error": lock_err}
    
    # Calculate new files size and validate total version size
    new_files_bytes = 0
    for file in files:
        file_content = await file.read()
        await file.seek(0)
        new_files_bytes += len(file_content)

    total_size = get_version_total_size(version_id, new_files_bytes=new_files_bytes)
    if total_size > MAX_VERSION_SIZE_BYTES:
        conn.close()
        return {"success": False, "error": "Không thể lưu do tổng dung lượng version vượt quá 40MB!"}
    
    is_v00 = version_id.startswith("V00_")
    if is_v00:
        if user["access_role"] != "Admin" and user["team"] != "Process DEV":
            conn.close()
            return Response(status_code=status.HTTP_403_FORBIDDEN)
        
        model_checklist_id = int(version_id.split("_")[1])
        cursor.execute("SELECT team, level_1, level_2 FROM model_checklist WHERE id = ?", (model_checklist_id,))
        item = cursor.fetchone()
        if not item:
            conn.close()
            return Response(status_code=404)
        s_team = "".join(c if c.isalnum() else "_" for c in item['team'])
        s_l1 = "".join(c if c.isalnum() else "_" for c in item['level_1'])
        s_l2 = "".join(c if c.isalnum() else "_" for c in item['level_2'])
        v_dir = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00").replace("\\", "/")
    else:
        version_id_int = int(version_id)
        v_dir = get_version_dir(version_id_int)
        
    if not v_dir:
        conn.close()
        return Response(status_code=404)
        
    os.makedirs(v_dir, exist_ok=True)
    
    uploaded_records = []
    
    for file in files:
        safe_filename = sanitize_folder_name(file.filename)
        file_path = os.path.join(v_dir, safe_filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        try:
            from backend.core.gdrive_storage import upload_file_to_gdrive
            rel_path = os.path.relpath(file_path, start=".")
            upload_file_to_gdrive(file_path, rel_path)
        except Exception as e:
            print(f"[GDRIVE SYNC ERROR] {e}")
            
        if not is_v00:
            cursor.execute("""
                INSERT INTO document_files (version_id, filename, filepath, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (version_id_int, safe_filename, file_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            uploaded_records.append({
                "id": cursor.lastrowid,
                "filename": safe_filename,
                "filepath": file_path
            })
        else:
            uploaded_records.append({
                "id": f"V00_{model_checklist_id}_{safe_filename}",
                "filename": safe_filename,
                "file_path": file_path
            })
            
    conn.commit()
    conn.close()
    
    return {"success": True, "files": uploaded_records}

# Xóa 1 File đính kèm
@router.delete("/api/documents/version/files/{file_id}")
async def api_delete_file(request: Request, file_id: str):
    user = get_current_user(request)
    if not user:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT version_id FROM document_files WHERE id = ?", (file_id,))
    f_row = cursor.fetchone()
    if f_row:
        v_id = f_row[0]
        cursor.execute("SELECT model_checklist_id FROM document_versions WHERE id = ?", (v_id,))
        v_row = cursor.fetchone()
        if v_row:
            lock_err = check_pessimistic_lock(cursor, v_row[0], user)
            if lock_err:
                conn.close()
                return {"success": False, "error": lock_err}
    
    if file_id.startswith("V00_"):
        if user["access_role"] != "Admin" and user["team"] != "Process DEV":
            conn.close()
            return Response(status_code=status.HTTP_403_FORBIDDEN)
            
        parts = file_id.split("_", 2)
        if len(parts) == 3:
            model_checklist_id = int(parts[1])
            filename = parts[2]
            cursor.execute("SELECT team, level_1, level_2 FROM model_checklist WHERE id = ?", (model_checklist_id,))
            item = cursor.fetchone()
            if item:
                s_team = "".join(c if c.isalnum() else "_" for c in item['team'])
                s_l1 = "".join(c if c.isalnum() else "_" for c in item['level_1'])
                s_l2 = "".join(c if c.isalnum() else "_" for c in item['level_2'])
                filepath = os.path.join(V00_TEMPLATES_PATH, s_team, s_l1, s_l2, "V00", filename).replace("\\", "/")
                if os.path.exists(filepath):
                    os.remove(filepath)
        conn.close()
        return {"success": True}

    file_id_int = int(file_id)
    cursor.execute("SELECT filepath FROM document_files WHERE id = ?", (file_id_int,))
    f = cursor.fetchone()
    if not f:
        conn.close()
        return Response(status_code=404)
        
    cursor.execute("DELETE FROM document_files WHERE id = ?", (file_id_int,))
    conn.commit()
    conn.close()
    
    if os.path.exists(f["filepath"]):
        os.remove(f["filepath"])
        
    return {"success": True}

# Hỗ trợ Client Download file
@router.get("/api/documents/version/files/{file_id}/download")
async def api_download_file(request: Request, file_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, filename FROM document_files WHERE id = ?", (file_id,))
    f = cursor.fetchone()
    conn.close()
    
    if not f or not os.path.exists(f["filepath"]):
        return Response(status_code=404)
        
    return FileResponse(f["filepath"], filename=f["filename"])
