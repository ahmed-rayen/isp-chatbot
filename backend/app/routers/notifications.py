# backend/app/routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Notification
from app.routers.auth import get_current_user
import uuid

router = APIRouter()

@router.get("/notifications")
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    return [{
        "id": str(n.id),
        "message": n.message,
        "is_read": n.is_read,
        "time": n.created_at.strftime("%Y-%m-%d %H:%M")
    } for n in notifs]

@router.patch("/notifications/{notif_id}/read")
def mark_as_read(notif_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == uuid.UUID(notif_id), Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "read"}