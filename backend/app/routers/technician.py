from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit
from app.routers.auth import get_current_user
from datetime import date

router = APIRouter()

# Dependency to ensure only technicians access this
def tech_required(current_user: User = Depends(get_current_user)):
    if not current_user.is_technician:
        raise HTTPException(status_code=403, detail="Technician privileges required")
    return current_user

@router.get("/tickets")
def get_tech_tickets(db: Session = Depends(get_db), current_user: User = Depends(tech_required)):
    visits = db.query(TechnicianVisit).filter(TechnicianVisit.technician_id == current_user.technician_id).all()
    
    result = []
    for v in visits:
        ticket = db.query(Ticket).filter(Ticket.id == v.ticket_id).first()
        if ticket and not ticket.is_deleted:
            client = db.query(User).filter(User.id == v.user_id).first()
            result.append({
                "ticket_id": ticket.id,
                "issue": ticket.issue_summary,
                "client_name": client.name if client else "Unknown",
                "client_address": client.address if client else "Unknown",
                "visit_date": v.scheduled_date.strftime("%Y-%m-%d"),
                "time_slot": v.time_slot,
                "status": ticket.status
            })
    return result

@router.get("/stats")
def get_tech_stats(db: Session = Depends(get_db), current_user: User = Depends(tech_required)):
    # Count resolved tickets for this technician
    resolved_count = db.query(Ticket).join(TechnicianVisit, Ticket.id == TechnicianVisit.ticket_id)\
        .filter(TechnicianVisit.technician_id == current_user.technician_id, Ticket.status == "resolved").count()
    
    upcoming_count = db.query(TechnicianVisit).filter(
        TechnicianVisit.technician_id == current_user.technician_id, 
        TechnicianVisit.scheduled_date >= date.today()
    ).count()
    
    return {"resolved": resolved_count, "upcoming": upcoming_count}

@router.patch("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, db: Session = Depends(get_db), current_user: User = Depends(tech_required)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.status = "resolved"
    db.commit()
    return {"status": "resolved"}