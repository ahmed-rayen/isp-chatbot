from sqlalchemy.orm import Session
from app.models.db_models import User, Notification
import uuid

def send_notification(db: Session, user_id: str, message: str):
    """Saves notification to DB and mocks sending an email."""
    try:
        # CAST TO UUID!
        notif = Notification(user_id=uuid.UUID(user_id), message=message)
        db.add(notif)
        db.commit()
        
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first() # CAST HERE TOO
        if user and user.email:
            print(f"📧 [MOCK EMAIL] To: {user.email} | Subject: Oassis Update | Body: {message}")
            
    except Exception as e:
        print(f"Notification failed: {e}")
        db.rollback() # Important: prevent session poisoning