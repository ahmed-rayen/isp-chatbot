from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Technician
from app.routers.auth import get_current_user

router = APIRouter()

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