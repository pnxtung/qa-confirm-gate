import sqlite3
import os
import re
from backend.core.config import DB_PATH, MP_READINESS_DATA_PATH

# Tạo kết nối CSDL trả về dạng Row Dictionary
def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Làm sạch tên thư mục (loại bỏ ký tự đặc biệt)
def sanitize_folder_name(name: str) -> str:
    if not name: return "Unknown"
    sanitized = re.sub(r'[\\\\/*?:"<>|]', "_", str(name)).strip()
    return sanitized if sanitized else "Unknown"

# Lấy đường dẫn thư mục vật lý từ ID checklist
def get_version_dir_from_checklist(model_checklist_id: int, version_no: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT model_id, team, level_1, level_2 FROM model_checklist WHERE id = ?", (model_checklist_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return ""
    model_id, team, level_1, level_2 = row
    
    cursor.execute("SELECT name FROM models WHERE id = ?", (model_id,))
    model_row = cursor.fetchone()
    conn.close()
    if not model_row:
        return ""
    model_name = model_row[0]
    
    s_model = sanitize_folder_name(model_name)
    s_team = sanitize_folder_name(team)
    s_l1 = sanitize_folder_name(level_1)
    s_l2 = sanitize_folder_name(level_2)
    return os.path.join(MP_READINESS_DATA_PATH, s_model, s_team, s_l1, s_l2, version_no).replace("\\", "/")

# Lấy đường dẫn thư mục vật lý từ ID version
def get_version_dir(version_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT model_checklist_id, version_no FROM document_versions WHERE id = ?", (version_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return ""
    return get_version_dir_from_checklist(row[0], row[1])

# Kiểm tra khóa tránh xung đột trên màn hình Config (Hết hạn sau 10 phút)
def check_pessimistic_config_lock(cursor, user):
    import time
    cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 1")
    row = cursor.fetchone()
    locked_at = row[0] if row and row[0] else 0
    locked_by = row[1] if row and row[1] else ""
    
    if locked_by and locked_by != user['fullname'] and int(time.time()) - locked_at < 600:
        return f"{locked_by} đang chỉnh sửa model config. Bạn không thể thao tác vào lúc này."
    if locked_by == user['fullname'] and int(time.time()) - locked_at >= 600:
        return "Khóa đã hết hạn, vui lòng tải lại trang."
    return None

# Kiểm tra khóa tránh xung đột trên màn hình Admin Management (Hết hạn sau 10 phút)
def check_pessimistic_admin_lock(cursor, user):
    import time
    cursor.execute("SELECT config_updated_at, last_updated_by FROM app_config WHERE id = 2")
    row = cursor.fetchone()
    locked_at = row[0] if row and row[0] else 0
    locked_by = row[1] if row and row[1] else ""
    
    if locked_by and locked_by != user['fullname'] and int(time.time()) - locked_at < 600:
        return f"{locked_by} đang chỉnh sửa Admin Management. Bạn không thể thao tác vào lúc này."
    if locked_by == user['fullname'] and int(time.time()) - locked_at >= 600:
        return "Khóa đã hết hạn, vui lòng tải lại trang."
    return None

# Kiểm tra khóa khi chỉnh sửa Document (Hết hạn sau 30 phút)
def check_pessimistic_lock(cursor, checklist_id, user):
    cursor.execute("SELECT locked_by, locked_at FROM model_checklist WHERE id = ?", (checklist_id,))
    lock_row = cursor.fetchone()
    if lock_row:
        import time
        locked_by, locked_at = lock_row[0], lock_row[1]
        username = user['fullname'] + ' (' + user['username'] + ')'
        if locked_by and locked_by != username:
            if locked_at and int(time.time()) - int(locked_at) < 1800:
                return f"{locked_by} đang chỉnh sửa, bạn không thể thao tác vào lúc này."
    return None

# Tính % tiến độ hoàn thành của từng Model
def get_model_statuses(cursor):
    cursor.execute("""
        SELECT mc.model_id, 
               COUNT(mc.id) as total_items, 
               SUM(CASE WHEN (
                   SELECT dv.status 
                   FROM document_versions dv 
                   WHERE dv.model_checklist_id = mc.id 
                   ORDER BY dv.id DESC LIMIT 1
               ) = 'Approved' THEN 1 ELSE 0 END) as approved_items
        FROM model_checklist mc
        GROUP BY mc.model_id
    """)
    stats = {}
    for r in cursor.fetchall():
        total = r['total_items']
        approved = r['approved_items'] or 0
        pct = f"{(approved / total * 100):.1f}%" if total > 0 else "0.0%"
        stats[r['model_id']] = pct
    return stats
