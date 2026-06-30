from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_required
from app.models.db_models import User, Technician, TechnicianVisit
from app.models.admin_schemas import VisitUpdate
from app.logger import logger

router = APIRouter()


@router.get("/technicians")
def get_technicians(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    techs = db.query(Technician).all()
    return [{"id": str(t.id), "name": t.name, "capacity": t.daily_capacity} for t in techs]


@router.patch("/visits/{ticket_id}")
def update_visit(
    ticket_id: str,
    payload: VisitUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket_id.upper()).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    try:
        visit.scheduled_date = date.fromisoformat(payload.scheduled_date)
    except Exception as e:
        logger.error(f"Admin visit update error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

    visit.time_slot = payload.time_slot
    visit.technician_id = payload.technician_id
    db.commit()
    return {"status": "updated", "ticket_id": ticket_id}