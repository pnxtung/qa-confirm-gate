import hashlib
import hmac
from fastapi import Request
from backend.core.database import get_db
from backend.core.config import SECRET_KEY

# Khóa bí mật mã hóa chữ ký Token
_SECRET_BYTES = SECRET_KEY.encode() if isinstance(SECRET_KEY, str) else SECRET_KEY

# Tạo chuỗi token dựa trên username
def create_token(user_data) -> str:
    if isinstance(user_data, dict):
        username = str(user_data.get("username", ""))
    else:
        username = str(user_data)
    signature = hmac.new(_SECRET_BYTES, username.encode(), hashlib.sha256).hexdigest()
    return f"{username}:{signature}"

# Xác minh tính hợp lệ của token
def verify_token(token: str):
    if not token or ":" not in token:
        return None
    username, signature = token.split(":", 1)
    expected_signature = hmac.new(_SECRET_BYTES, username.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(signature, expected_signature):
        return username
    return None

# Dependency lấy thông tin user hiện tại từ cookie
def get_current_user(request: Request):
    token = request.cookies.get("access_token") or request.cookies.get("auth_token")
    username = verify_token(token)
    if not username:
        return None
    
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
    finally:
        conn.close()
    return user
