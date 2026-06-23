from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Technician
from app.routers.auth import get_current_user
from datetime import date

router = APIRouter()

class TicketUpdate(BaseModel):
    status: str

class VisitUpdate(BaseModel):
    scheduled_date: str
    time_slot: str
    technician_id: str
    
# Custom dependency: Only admins can pass!
def admin_required(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

@router.get("/tickets")
def get_all_tickets(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    
    result = []
    for t in tickets:
        user = db.query(User).filter(User.id == t.user_id).first()
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
            "client_name": user.name if user else "Unknown",
            "client_account": user.account_number if user else "N/A",
            "issue": t.issue_summary,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "technician": tech_name,
            "visit_date": visit_date,
            "visit_slot": visit_slot,
            "transcript": t.transcript if t.transcript else "No transcript recorded."
        })
    return result

@router.patch("/tickets/{ticket_id}")
def update_ticket_status(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = payload.status
    db.commit()
    return {"status": "updated", "ticket_id": ticket.id, "new_status": ticket.status}

# --- NEW: Reschedule Technician Visit ---
@router.patch("/visits/{ticket_id}")
def update_visit(ticket_id: str, payload: VisitUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket_id.upper()).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    # Update fields
    try:
        visit.scheduled_date = date.fromisoformat(payload.scheduled_date)
    except:
        pass # Ignore bad date format
    
    visit.time_slot = payload.time_slot
    visit.technician_id = payload.technician_id
    
    db.commit()
    return {"status": "updated", "ticket_id": ticket_id}
@router.get("/technicians")
def get_technicians(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    techs = db.query(Technician).all()
    return [{"id": str(t.id), "name": t.name, "capacity": t.daily_capacity} for t in techs]