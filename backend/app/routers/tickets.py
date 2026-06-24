# backend/app/routers/tickets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Technician, Feedback
from app.routers.auth import get_current_user

router = APIRouter()

@router.get("/tickets")
def get_user_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tickets = db.query(Ticket).filter(Ticket.user_id == current_user.id).order_by(Ticket.created_at.desc()).all()
    
    result = []
    for t in tickets:
        # Initialize variables so they always exist!
        tech_name = None
        visit_date = None
        visit_slot = None
        
        visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == t.id).first()
        if visit:
            tech = db.query(Technician).filter(Technician.id == visit.technician_id).first()
            tech_name = tech.name if tech else "Unassigned"
            visit_date = visit.scheduled_date.strftime("%Y-%m-%d") if visit.scheduled_date else None
            visit_slot = visit.time_slot
            
        result.append({
            "id": t.id,
            "session_id": str(t.session_id), # Needed for feedback loop
            "issue": t.issue_summary,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "technician": tech_name,
            "visit_date": visit_date,
            "visit_slot": visit_slot,
            "transcript": t.transcript if t.transcript else "No transcript recorded."
        })
    return result

@router.get("/tickets/{ticket_id}/needs-feedback")
async def needs_feedback(ticket_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.user_id == current_user.id,
        Ticket.status == "resolved"
    ).first()
    if not ticket:
        return {"needs_feedback": False}
    
    existing = db.query(Feedback).filter(Feedback.ticket_id == ticket_id).first()
    return {"needs_feedback": existing is None}
