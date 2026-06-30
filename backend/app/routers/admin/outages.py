from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.deps import admin_required
from app.models.db_models import User, Outage
from app.models.admin_schemas import OutageCreate

router = APIRouter()


@router.get("/outages")
def get_outages(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    outages = db.query(Outage).filter(Outage.is_deleted.is_(False)).all()
    return [{"city": o.city, "status": o.status, "is_active": o.is_active} for o in outages]


@router.post("/outages")
def create_outage(
    payload: OutageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    existing = db.query(Outage).filter(func.lower(Outage.city) == payload.city.lower()).first()

    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            existing.status = payload.status
            existing.is_active = True
        else:
            raise HTTPException(status_code=400, detail="Outage already exists")
    else:
        db.add(Outage(city=payload.city.lower(), status=payload.status, is_active=True))

    db.commit()
    return {"status": "created"}


@router.patch("/outages/{city}")
def toggle_outage(
    city: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    outage = (
        db.query(Outage)
        .filter(func.lower(Outage.city) == city.lower(), Outage.is_deleted.is_(False))
        .first()
    )
    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")

    outage.is_active = not outage.is_active
    db.commit()
    return {"city": outage.city, "is_active": outage.is_active}


@router.delete("/outages/{city}")
def delete_outage(
    city: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    outage = (
        db.query(Outage)
        .filter(func.lower(Outage.city) == city.lower(), Outage.is_deleted.is_(False))
        .first()
    )
    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")

    outage.is_deleted = True
    outage.is_active = False
    db.commit()
    return {"status": "deleted"}