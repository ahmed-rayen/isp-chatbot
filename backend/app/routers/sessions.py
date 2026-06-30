import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.logger import logger
from app.routers.auth import get_current_user
from app.models.db_models import User, ChatSession, Message, SessionSummary
from app.services.session import get_full_history

router = APIRouter()


def _get_owned_session(db: Session, session_id: str, user_id) -> ChatSession:
    """Fetch a session and verify it belongs to the current user."""
    try:
        uid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    session = db.query(ChatSession).filter(ChatSession.id == uid, ChatSession.user_id == user_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [{"id": str(s.id), "title": s.title} for s in sessions]


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_session(db, session_id, current_user.id)  # Ownership check

    msgs = (
        db.query(Message)
        .filter(Message.session_id == uuid.UUID(session_id))
        .order_by(Message.created_at)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in msgs]


@router.post("/sessions/{session_id}/summarize")
async def summarize_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_session(db, session_id, current_user.id)  # Ownership check

    history = get_full_history(db, session_id)
    if len(history) < 2:
        return {"status": "skipped", "message": "Not enough messages to summarize."}

    try:
        from app.services.nvidia_client import generate_session_summary

        summary_text, status = await generate_session_summary(history)
        db.add(SessionSummary(
            user_id=current_user.id,
            session_id=uuid.UUID(session_id),
            summary=summary_text,
            status=status,
        ))
        db.commit()
        return {"status": "summarized", "summary": summary_text}
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_owned_session(db, session_id, current_user.id)

    try:
        db.delete(session)  # Cascade deletes messages, summaries, tickets, visits, kb_hits
        db.commit()
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")