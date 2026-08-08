from fastapi import APIRouter, Request, status, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import datetime
from backend.core.database import get_db
from backend.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

class AboutUsRequest(BaseModel):
    content: str

class FeedbackSubmitRequest(BaseModel):
    content: str

# Render trang Feedback
@router.get("/feedback")
def get_feedback(request: Request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        return templates.TemplateResponse(
            request=request,
            name="about_us.html",
            context={"current_user": dict(user)}
        )
    finally:
        conn.close()

# Get Data
@router.get("/api/feedback/data")
def get_feedback_data(request: Request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
            
        # 1. Lấy About Us
        cursor.execute("SELECT about_us FROM site_content WHERE id = 1")
        row = cursor.fetchone()
        about_us = row['about_us'] if row else ""
        
        # 2. Lấy Access Stats
        cursor.execute("SELECT SUM(access_count) FROM access_logs")
        row_total = cursor.fetchone()
        total_access = row_total[0] if row_total and row_total[0] else 0
        
        today = datetime.date.today()
        start_of_month = today.replace(day=1).isoformat()
        cursor.execute("SELECT SUM(access_count) FROM access_logs WHERE access_date >= ?", (start_of_month,))
        row_month = cursor.fetchone()
        this_month_access = row_month[0] if row_month and row_month[0] else 0
        
        # 3. Lấy Feedbacks từ Postgres
        cursor.execute("SELECT id, employee_id, timestamp, content FROM feedbacks ORDER BY id DESC")
        rows = cursor.fetchall()
        feedbacks = []
        for r in rows:
            ts_str = str(r['timestamp']) if r['timestamp'] else ""
            feedbacks.append({
                "id": str(r['id']),
                "employee_id": r['employee_id'] or "",
                "time": ts_str,
                "content": r['content'] or ""
            })
                
        return JSONResponse({
            "about_us": about_us,
            "total_access": total_access,
            "this_month": this_month_access,
            "feedbacks": feedbacks
        })
    finally:
        conn.close()

# Cập nhật About Us
@router.post("/api/feedback/about")
def update_about_us(request: Request, data: AboutUsRequest):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user or user['username'] != 'ADMINPNX':
            raise HTTPException(status_code=403, detail="Forbidden")
            
        cursor.execute("UPDATE site_content SET about_us = ? WHERE id = 1", (data.content,))
        conn.commit()
        return JSONResponse({"status": "success", "message": "Updated successfully"})
    finally:
        conn.close()

# Gửi Feedback
@router.post("/api/feedback/submit")
def submit_feedback(request: Request, data: FeedbackSubmitRequest):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
            
        if len(data.content) > 1000:
            raise HTTPException(status_code=400, detail="Content too long")
            
        # Kiểm tra Spam (10 phút)
        cursor.execute("SELECT timestamp FROM feedbacks WHERE employee_id = ? ORDER BY id DESC LIMIT 1", (user['username'],))
        row = cursor.fetchone()
        if row and row['timestamp']:
            try:
                last_time = row['timestamp']
                if isinstance(last_time, str):
                    last_time = datetime.datetime.fromisoformat(last_time)
                if (datetime.datetime.now() - last_time).total_seconds() < 600:
                    return JSONResponse(
                        status_code=429,
                        content={"status": "error", "message": "Phát hiện đối tượng spam feedback"}
                    )
            except Exception:
                pass
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO feedbacks (employee_id, timestamp, content) VALUES (?, ?, ?)", 
                       (user['username'], now_str, data.content))
        conn.commit()
        return JSONResponse({"status": "success"})
    finally:
        conn.close()

# Xóa Feedback
@router.delete("/api/feedback/{feedback_id}")
def delete_feedback(request: Request, feedback_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        user = get_current_user(request, cursor=cursor)
        if not user or user['username'] != 'ADMINPNX':
            raise HTTPException(status_code=403, detail="Forbidden")
            
        cursor.execute("DELETE FROM feedbacks WHERE id = ?", (feedback_id,))
        conn.commit()
        return JSONResponse({"status": "success"})
    finally:
        conn.close()
