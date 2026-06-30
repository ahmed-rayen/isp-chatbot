from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
# Import your database dependency and auth dependencies
from ..database import get_db 
from ..services.auth import get_current_user, require_admin, require_client
from ..models.db_models import Bill, User
from ..models.schemas import BillCreate, BillOut

router = APIRouter(prefix="/billing", tags=["Billing"])

# Admin endpoint to generate a bill for a user
@router.post("/", response_model=BillOut)
def create_bill(bill: BillCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    new_bill = Bill(**bill.dict())
    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)
    return new_bill

# Admin endpoint to get all bills
@router.get("/all", response_model=List[BillOut])
def get_all_bills(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    bills = db.query(Bill).all()
    return bills

# Client endpoint to get their own bills
@router.get("/my-bills", response_model=List[BillOut])
def get_my_bills(db: Session = Depends(get_db), current_user: User = Depends(require_client)):
    bills = db.query(Bill).filter(Bill.user_id == current_user.id).all()
    return bills

# Client/Admin endpoint to mark a bill as paid (Simulated payment)
@router.put("/{bill_id}/pay", response_model=BillOut)
def pay_bill(bill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Ensure clients can only pay their own bills
    if current_user.role == "client" and bill.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this bill")
        
    bill.status = "paid"
    from datetime import datetime
    bill.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(bill)
    return bill