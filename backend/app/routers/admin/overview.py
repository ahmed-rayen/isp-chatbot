from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_required
from app.models.db_models import User, Ticket, Outage, FlaggedKBChunk

router = APIRouter()


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    total_tickets = db.query(Ticket).filter(Ticket.is_deleted.is_(False)).count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved", Ticket.is_deleted.is_(False)).count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open", Ticket.is_deleted.is_(False)).count()
    active_outages = db.query(Outage).filter(Outage.is_active.is_(True), Outage.is_deleted.is_(False)).count()

    return {
        "total_tickets": total_tickets,
        "resolved_tickets": resolved_tickets,
        "open_tickets": open_tickets,
        "active_outages": active_outages,
        "resolution_rate": round((resolved_tickets / total_tickets * 100), 1) if total_tickets > 0 else 0,
    }


@router.get("/flagged-chunks")
def get_flagged_chunks(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    chunks = db.query(FlaggedKBChunk).filter(FlaggedKBChunk.reviewed.is_(False)).all()
    return [{"id": str(c.id), "chunk_text": c.chunk_text, "topic": c.topic} for c in chunks]


@router.patch("/flagged-chunks/{chunk_id}/review")
def review_chunk(
    chunk_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    chunk = db.query(FlaggedKBChunk).filter(FlaggedKBChunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    chunk.reviewed = True
    db.commit()
    return {"status": "reviewed"}