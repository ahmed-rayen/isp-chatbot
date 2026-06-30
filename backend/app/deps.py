from fastapi import Depends, HTTPException
from app.models.db_models import User
from app.routers.auth import get_current_user


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user