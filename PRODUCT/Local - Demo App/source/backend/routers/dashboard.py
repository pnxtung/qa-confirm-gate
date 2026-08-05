from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.database import get_db, get_model_statuses
from backend.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

# Render trang chủ Dashboard
@router.get("/")
async def get_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM models ORDER BY sort_order ASC, id ASC")
    models = [dict(m) for m in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM models WHERE activate = 'Yes' ORDER BY sort_order ASC, id ASC")
    active_models = [dict(m) for m in cursor.fetchall()]
    
    # Tính toán tiến độ % hoàn thành của model
    stats = get_model_statuses(cursor)
    for m in models:
        m['status_percent'] = stats.get(m['id'], "0.0%")
    for m in active_models:
        m['status_percent'] = stats.get(m['id'], "0.0%")
        
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"current_user": dict(user), "models": models, "active_models": active_models}
    )
