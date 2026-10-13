from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ContactMessage
from schemas import ContactCreate, ContactResponse

router = APIRouter(prefix="/api/v1/contact", tags=["Contact & Support"])


@router.post("", response_model=ContactResponse)
def submit_contact_message(contact: ContactCreate, db: Session = Depends(get_db)):
    msg = ContactMessage(
        name=contact.name,
        email=contact.email,
        message=contact.message,
    )
    db.add(msg)
    db.commit()
    return ContactResponse(
        success=True,
        message="Thank you for reaching out! Our branch team has received your message and will respond shortly."
    )


@router.get("/branch-info")
def get_branch_info():
    """Branch details matching the footer and contact page of https://queue-wiz-home.lovable.app"""
    return {
        "bank_name": "BankQueue Main Branch",
        "address": "ABC Bank, Main Branch, College Road, Chennai",
        "phone": "+91 1800 123 456",
        "email": "support@bankqueue.example",
        "working_hours": "Monday – Saturday, 9:00 AM – 4:00 PM (Closed on Sundays & Bank Holidays)",
        "advance_booking_days": 2,
    }
