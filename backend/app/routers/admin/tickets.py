from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.deps import admin_required
from app.models.db_models import User, Ticket, TechnicianVisit, Technician, Notification, TicketComment
from app.models.admin_schemas import TicketStatusUpdate, CommentCreate
from app.logger import logger

router = APIRouter()


@router.get("/tickets")
def get_all_tickets(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    # Single query with joins — eliminates the N+1 problem
    rows = (
        db.query(
            Ticket,
            User.name,
            User.account_number,
            Technician.name,
            TechnicianVisit.scheduled_date,
            TechnicianVisit.time_slot,
        )
        .outerjoin(User, Ticket.user_id == User.id)
        .outerjoin(TechnicianVisit, Ticket.id == TechnicianVisit.ticket_id)
        .outerjoin(Technician, TechnicianVisit.technician_id == Technician.id)
        .filter(Ticket.is_deleted.is_(False))
        .order_by(Ticket.created_at.desc())
        .all()
    )

    return [
        {
            "id": t.id,
            "client_name": user_name or "Unknown",
            "client_account": user_account or "N/A",
            "issue": t.issue_summary,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "technician": tech_name,
            "visit_date": visit_date.strftime("%Y-%m-%d") if visit_date else None,
            "visit_slot": visit_slot,
            "transcript": t.transcript or "No transcript recorded.",
        }
        for t, user_name, user_account, tech_name, visit_date, visit_slot in rows
    ]


@router.patch("/tickets/{ticket_id}")
def update_ticket_status(
    ticket_id: str,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = payload.status

    if payload.status == "resolved":
        db.add(Notification(
            user_id=ticket.user_id,
            message=f"Your issue ({ticket.id}) has been resolved. Please rate your experience.",
        ))

    db.commit()
    return {"status": "updated", "ticket_id": ticket.id, "new_status": ticket.status}


@router.patch("/tickets/{ticket_id}/archive")
def archive_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.is_deleted = True
    db.commit()
    return {"status": "archived"}


@router.post("/tickets/{ticket_id}/comments")
def add_comment(
    ticket_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.add(TicketComment(ticket_id=ticket.id, user_id=admin.id, content=payload.content))
    db.add(Notification(
        user_id=ticket.user_id,
        message=f"New message on your ticket {ticket.id}: {payload.content[:50]}...",
    ))
    db.commit()
    return {"status": "comment_added"}


@router.get("/tickets/{ticket_id}/comments")
def get_comments(
    ticket_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    comments = (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket_id.upper())
        .order_by(TicketComment.created_at)
        .all()
    )
    return [{"content": c.content, "time": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in comments]