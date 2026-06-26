# backend/app/routers/tickets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import User, Ticket, TechnicianVisit, Feedback, TicketComment, Notification,Technician
from app.routers.auth import get_current_user
from pydantic import BaseModel
from app.database import get_db

router = APIRouter()
class CommentRequest(BaseModel):
    content: str
    
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

@router.get("/tickets/{ticket_id}/comments")
async def get_ticket_comments(ticket_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    comments = db.query(TicketComment).filter(TicketComment.ticket_id == ticket.id).order_by(TicketComment.created_at).all()
    result = []
    for c in comments:
        sender = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "content": c.content,
            "time": c.created_at.strftime("%Y-%m-%d %H:%M"),
            "sender_name": sender.name if sender else "Unknown",
            "sender_role": "Technician" if (sender and sender.is_technician) else "Client"
        })
    return result

# NEW: Post a comment (Accessible by Client and Tech)
@router.post("/tickets/{ticket_id}/comments")
async def add_ticket_comment(ticket_id: str, payload: CommentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    # Admins supervise but don't chat. Only Client or assigned Tech can post.
    if current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admins cannot reply to tickets directly.")
        
    comment = TicketComment(ticket_id=ticket.id, user_id=current_user.id, content=payload.content)
    db.add(comment)
    
    # Notify the other party
    if current_user.is_technician:
        # Tech replied -> Notify Client
        db.add(Notification(user_id=ticket.user_id, message=f"New update on your ticket {ticket.id}: {payload.content[:50]}..."))
    else:
        # Client replied -> Notify Tech
        visit = db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket.id).first()
        if visit:
            tech_user = db.query(User).filter(User.technician_id == visit.technician_id).first()
            if tech_user:
                db.add(Notification(user_id=tech_user.id, message=f"New message on ticket {ticket.id}: {payload.content[:50]}..."))
                
    db.commit()
    return {"status": "comment_added"}