from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import BankService
from schemas import ServiceOut

router = APIRouter(prefix="/api/v1/services", tags=["Services"])


@router.get("", response_model=List[ServiceOut])
def get_services(db: Session = Depends(get_db)):
    """Fetch all active banking services offered at the branch."""
    return db.query(BankService).filter(BankService.is_active == True).all()


@router.get("/{service_id}", response_model=ServiceOut)
def get_service_by_id(service_id: int, db: Session = Depends(get_db)):
    service = db.query(BankService).filter(BankService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
