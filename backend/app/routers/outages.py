from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Outage, User
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/outages/active")
def get_active_outages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    outages = db.query(Outage).filter(Outage.is_active.is_(True), Outage.is_deleted.is_(False)).all()
    return [{"city": o.city, "status": o.status} for o in outages]