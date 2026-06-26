from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Technician, Outage,Notification, FlaggedKBChunk, TicketComment
from app.routers.auth import get_current_user
from datetime import date
from sqlalchemy import func
from app.logger import logger # <-- ADD THIS


router = APIRouter()

class OutageCreate(BaseModel):
    city: str
    status: str

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
    
    # TRIGGER NOTIFICATION ON RESOLVE
    if payload.status == "resolved":
        notif = Notification(
            user_id=ticket.user_id,
            message=f"Your issue ({ticket.id}) has been resolved. Please rate your experience."
        )
        db.add(notif)
        
    db.commit()
    return {"status": "updated", "ticket_id": ticket.id, "new_status": ticket.status}
@router.get("/flagged-chunks")
def get_flagged_chunks(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    chunks = db.query(FlaggedKBChunk).filter(FlaggedKBChunk.reviewed == False).all()
    return [{"id": str(c.id), "chunk_text": c.chunk_text, "topic": c.topic} for c in chunks]

# NEW: Mark Flagged Chunk as Reviewed
@router.patch("/flagged-chunks/{chunk_id}/review")
def review_chunk(chunk_id: str, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    chunk = db.query(FlaggedKBChunk).filter(FlaggedKBChunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    chunk.reviewed = True
    db.commit()
    return {"status": "reviewed"}
# --- NEW: Reschedule Technician Visit ---
@router.patch("/visits/{ticket_id}")
def update_visit(ticket_id: str, payload: VisitUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket_id.upper()).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    try:
        visit.scheduled_date = date.fromisoformat(payload.scheduled_date)
    except Exception as e:
        logger.error(f"Admin error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")
    
    visit.time_slot = payload.time_slot
    visit.technician_id = payload.technician_id
    db.commit()
    return {"status": "updated", "ticket_id": ticket_id}

@router.get("/technicians")
def get_technicians(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    techs = db.query(Technician).all()
    return [{"id": str(t.id), "name": t.name, "capacity": t.daily_capacity} for t in techs]

@router.patch("/tickets/{ticket_id}/archive")
def archive_ticket(ticket_id: str, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.is_deleted = True # Soft delete!
    db.commit()
    return {"status": "archived"}

class CommentRequest(BaseModel):
    content: str

@router.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: str, payload: CommentRequest, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    comment = TicketComment(ticket_id=ticket.id, user_id=admin.id, content=payload.content)
    db.add(comment)
    
    # Notify the client
    notif = Notification(user_id=ticket.user_id, message=f"New message on your ticket {ticket.id}: {payload.content[:50]}...")
    db.add(notif)
    db.commit()
    return {"status": "comment_added"}

@router.get("/tickets/{ticket_id}/comments")
def get_comments(ticket_id: str, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    comments = db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id.upper()).order_by(TicketComment.created_at).all()
    return [{"content": c.content, "time": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in comments]

@router.get("/outages")
def get_outages(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    outages = db.query(Outage).filter(Outage.is_deleted == False).all()
    return [{"city": o.city, "status": o.status, "is_active": o.is_active} for o in outages]

@router.post("/outages")
def create_outage(payload: OutageCreate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    # Case-insensitive check if city already exists
    existing = db.query(Outage).filter(func.lower(Outage.city) == payload.city.lower()).first()
    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            existing.status = payload.status
            existing.is_active = True
        else:
            raise HTTPException(status_code=400, detail="Outage already exists")
    else:
        outage = Outage(city=payload.city.lower(), status=payload.status, is_active=True)
        db.add(outage)
    db.commit()
    return {"status": "created"}

@router.patch("/outages/{city}")
def toggle_outage(city: str, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    # Case-insensitive search
    outage = db.query(Outage).filter(func.lower(Outage.city) == city.lower(), Outage.is_deleted == False).first()
    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")
    
    outage.is_active = not outage.is_active
    db.commit()
    return {"city": outage.city, "is_active": outage.is_active}

@router.delete("/outages/{city}")
def delete_outage(city: str, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    # Case-insensitive search
    outage = db.query(Outage).filter(func.lower(Outage.city) == city.lower(), Outage.is_deleted == False).first()
    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")
    
    # SOFT DELETE
    outage.is_deleted = True
    outage.is_active = False
    db.commit()
    return {"status": "deleted"}

@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    total_tickets = db.query(Ticket).count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved").count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()
    active_outages = db.query(Outage).filter(Outage.is_active == True, Outage.is_deleted == False).count()
    
    return {
        "total_tickets": total_tickets,
        "resolved_tickets": resolved_tickets,
        "open_tickets": open_tickets,
        "active_outages": active_outages,
        "resolution_rate": round((resolved_tickets / total_tickets * 100), 1) if total_tickets > 0 else 0
    }