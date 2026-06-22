from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Technician
from app.routers.auth import get_current_user

router = APIRouter()

@router.get("/tickets")
def get_user_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tickets = db.query(Ticket).filter(Ticket.user_id == current_user.id).order_by(Ticket.created_at.desc()).all()
    
    result = []
    for t in tickets:
        # Check if there is a technician visit attached
        visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == t.id).first()
        tech_name = None
        visit_date = None
        visit_slot = None
        
        if visit:
            tech = db.query(Technician).filter(Technician.id == visit.technician_id).first()
            tech_name = tech.name if tech else "Unassigned"
            visit_date = visit.scheduled_date.strftime("%Y-%m-%d") if visit.scheduled_date else None
            visit_slot = visit.time_slot
            
        result.append({
            "id": t.id,
            "issue": t.issue_summary,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "technician": tech_name,
            "visit_date": visit_date,
            "visit_slot": visit_slot
        })
    return result