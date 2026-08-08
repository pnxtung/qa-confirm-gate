from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.database import get_db, get_model_statuses
from backend.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/")
def get_dashboard(request: Request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        user = get_current_user(request, cursor=cursor)
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # Ghi nhận lượt truy cập (Access Log)
        import datetime
        today = datetime.date.today().isoformat()
        cursor.execute("""
            INSERT INTO access_logs (access_date, access_count) 
            VALUES (?, 1) 
            ON CONFLICT (access_date) 
            DO UPDATE SET access_count = access_logs.access_count + 1
        """, (today,))
        conn.commit()
        
        cursor.execute("SELECT * FROM models ORDER BY sort_order ASC, id ASC")
        models = [dict(m) for m in cursor.fetchall()]
        active_models = [m for m in models if m['activate'] == 'Yes']
        
        # Tính toán tiến độ % hoàn thành của model
        stats = get_model_statuses(cursor)
        for m in models:
            m['status_percent'] = stats.get(m['id'], "0.0%")
        for m in active_models:
            m['status_percent'] = stats.get(m['id'], "0.0%")
    finally:
        conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"current_user": dict(user), "models": models, "active_models": active_models}
    )


