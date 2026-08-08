from fastapi import APIRouter, Request, status, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import csv
import datetime
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.storage_adapter import StorageAdapter

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

FEEDBACKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../User Data/feedbacks"))
FEEDBACKS_CSV_PATH = os.path.join(FEEDBACKS_DIR, "feedbacks.csv")

class AboutUsRequest(BaseModel):
    content: str

class FeedbackSubmitRequest(BaseModel):
    content: str

def init_csv():
    if not os.path.exists(FEEDBACKS_DIR):
        os.makedirs(FEEDBACKS_DIR, exist_ok=True)
    if not os.path.exists(FEEDBACKS_CSV_PATH):
        with open(FEEDBACKS_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Employee ID", "Timestamp", "Content"])

# Render trang Feedback
@router.get("/feedback")
async def get_feedback(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request=request,
        name="about_us.html",
        context={"current_user": dict(user)}
    )

# Get Data
@router.get("/api/feedback/data")
async def get_feedback_data(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Lấy About Us
    cursor.execute("SELECT about_us FROM site_content WHERE id = 1")
    row = cursor.fetchone()
    about_us = row['about_us'] if row else ""
    
    # 2. Lấy Access Stats
    # Total
    cursor.execute("SELECT SUM(access_count) FROM access_logs")
    row_total = cursor.fetchone()
    total_access = row_total[0] if row_total and row_total[0] else 0
    
    # This Month
    today = datetime.date.today()
    start_of_month = today.replace(day=1).isoformat()
    cursor.execute("SELECT SUM(access_count) FROM access_logs WHERE access_date >= ?", (start_of_month,))
    row_month = cursor.fetchone()
    this_month_access = row_month[0] if row_month and row_month[0] else 0
    
    conn.close()
    
    # 3. Đọc CSV lấy Feedbacks
    feedbacks = []
    init_csv()
    with open(FEEDBACKS_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("ID") or not str(r.get("ID")).strip():
                continue
            feedbacks.append({
                "id": r.get("ID", ""),
                "employee_id": r.get("Employee ID", ""),
                "time": r.get("Timestamp", ""),
                "content": r.get("Content", "")
            })
    feedbacks.reverse() # Hiện mới nhất lên trên
            
    return JSONResponse({
        "about_us": about_us,
        "total_access": total_access,
        "this_month": this_month_access,
        "feedbacks": feedbacks
    })

# Cập nhật About Us
@router.post("/api/feedback/about")
async def update_about_us(request: Request, data: AboutUsRequest, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user or user['username'] != 'ADMINPNX':
        raise HTTPException(status_code=403, detail="Forbidden")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE site_content SET about_us = ? WHERE id = 1", (data.content,))
    conn.commit()
    conn.close()
    
    StorageAdapter.sync_database(background_tasks)
    
    return JSONResponse({"status": "success", "message": "Updated successfully"})

# Gửi Feedback
@router.post("/api/feedback/submit")
async def submit_feedback(request: Request, data: FeedbackSubmitRequest, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if len(data.content) > 1000:
        raise HTTPException(status_code=400, detail="Content too long")
        
    init_csv()
    
    # Kiểm tra Spam (10 phút)
    last_time_str = None
    with open(FEEDBACKS_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("Employee ID") == user['username']:
                last_time_str = r.get("Timestamp", "")
                
    if last_time_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M"):
            try:
                last_time = datetime.datetime.strptime(last_time_str, fmt)
                if (datetime.datetime.now() - last_time).total_seconds() < 600:
                    return JSONResponse(
                        status_code=429,
                        content={"status": "error", "message": "Phát hiện đối tượng spam feedback"}
                    )
                break
            except ValueError:
                pass
    
    # Lấy ID mới (đếm số dòng)
    new_id = 1
    with open(FEEDBACKS_CSV_PATH, "r", encoding="utf-8-sig") as f:
        new_id = sum(1 for line in f) # Header is line 1, so row 1 has ID 1, row 2 has ID 2
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    employee_id = user['username']
    
    with open(FEEDBACKS_CSV_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([new_id, employee_id, timestamp, data.content])
        
    StorageAdapter.sync_feedbacks_csv(background_tasks)
        
    return JSONResponse({"status": "success"})

# Xóa Feedback
@router.delete("/api/feedback/{feedback_id}")
async def delete_feedback(request: Request, feedback_id: str, background_tasks: BackgroundTasks):
    user = get_current_user(request)
    if not user or user['username'] != 'ADMINPNX':
        raise HTTPException(status_code=403, detail="Forbidden")
        
    init_csv()
    
    rows = []
    with open(FEEDBACKS_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    # header = rows[0], data = rows[1:]
    if len(rows) > 0:
        header = rows[0]
        data_rows = rows[1:]
        # Filter out the row with the matching ID, and also any corrupted empty rows
        new_data = [r for r in data_rows if len(r) > 0 and str(r[0]).strip() != "" and r[0] != feedback_id]
        
        with open(FEEDBACKS_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_data)
            
        StorageAdapter.sync_feedbacks_csv(background_tasks)
            
    return JSONResponse({"status": "success"})
