from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.db_models import User, Feedback, KBHit, FlaggedKBChunk, Ticket
from app.routers.auth import get_current_user
import uuid

router = APIRouter()

class FeedbackRequest(BaseModel):
    session_id: str
    ticket_id: str
    rating: int
    comment: str = None

@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    feedback = Feedback(
        user_id=current_user.id,
        session_id=uuid.UUID(payload.session_id),
        ticket_id=payload.ticket_id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(feedback)
    db.flush()

    # If rating is low, flag the KB chunks retrieved during this session
    if payload.rating <= 2:
        kb_hits = db.query(KBHit).filter(KBHit.session_id == uuid.UUID(payload.session_id)).all()
        for hit in kb_hits:
            db.add(FlaggedKBChunk(
                feedback_id=feedback.id,
                chunk_text=hit.chunk_text,
                topic=hit.topic
            ))
    db.commit()
    return {"status": "submitted"}