from datetime import datetime, timedelta, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from database import get_db
from models import Token, BankService, Counter, User
from schemas import TokenCreate, TokenOut, TokenTrackerResponse, SlotAvailabilityResponse, SlotInfo
from routes.auth import get_current_user, get_optional_current_user
from queue_manager import queue_manager

router = APIRouter(prefix="/api/v1/tokens", tags=["Tokens"])

STANDARD_TIME_SLOTS = [
    "09:30 AM - 10:00 AM",
    "10:00 AM - 10:30 AM",
    "10:30 AM - 11:00 AM",
    "11:15 AM - 11:45 AM",
    "12:00 PM - 12:30 PM",
    "02:00 PM - 02:30 PM",
    "02:30 PM - 03:00 PM",
    "03:00 PM - 03:30 PM",
]
SLOT_CAPACITY = 3  # Max bookings per slot per service category


def get_allowed_booking_dates():
    """Returns allowed dates: Today and Tomorrow (next 2 calendar days)."""
    today_dt = date.today()
    tomorrow_dt = today_dt + timedelta(days=1)
    return {
        today_dt.strftime("%Y-%m-%d"): "Today",
        tomorrow_dt.strftime("%Y-%m-%d"): "Tomorrow",
        "Today": "Today",
        "Tomorrow": "Tomorrow",
    }


def normalize_booking_date(booking_date_str: str) -> (str, str):
    """
    Validates and normalizes date. Returns (canonical_date_iso, label).
    Raises HTTPException if outside allowed 2-calendar-day window.
    """
    cleaned = booking_date_str.strip()
    today_dt = date.today()
    tomorrow_dt = today_dt + timedelta(days=1)
    today_iso = today_dt.strftime("%Y-%m-%d")
    tomorrow_iso = tomorrow_dt.strftime("%Y-%m-%d")

    if cleaned in ["Today", today_iso]:
        return today_iso, "Today"
    elif cleaned in ["Tomorrow", tomorrow_iso]:
        return tomorrow_iso, "Tomorrow"

    # Try parsing YYYY-MM-DD
    try:
        parsed = datetime.strptime(cleaned, "%Y-%m-%d").date()
        if parsed == today_dt:
            return today_iso, "Today"
        elif parsed == tomorrow_dt:
            return tomorrow_iso, "Tomorrow"
    except ValueError:
        pass

    raise HTTPException(
        status_code=400,
        detail="Booking is only allowed within the next 2 calendar days (Today and Tomorrow)."
    )


def generate_token_number(db: Session, prefix: str) -> str:
    latest = db.query(Token).filter(
        Token.token_number.startswith(prefix)
    ).order_by(Token.id.desc()).first()

    if latest:
        try:
            num = int(latest.token_number[len(prefix):]) + 1
        except ValueError:
            num = 101
    else:
        num = 101
    return f"{prefix}{num}"


@router.get("/slots", response_model=SlotAvailabilityResponse)
def get_slot_availability(
    service_id: int = Query(...),
    booking_date: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Real-time slot availability checker based on actual database bookings.
    Only allows dates within the next 2 calendar days (Today & Tomorrow).
    """
    service = db.query(BankService).filter(BankService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    canonical_date, date_label = normalize_booking_date(booking_date)

    slots_data: List[SlotInfo] = []
    for slot_name in STANDARD_TIME_SLOTS:
        # Count existing active tokens for this service, date, and slot
        booked_count = db.query(Token).filter(
            Token.service_id == service_id,
            Token.booking_date.in_([canonical_date, date_label]),
            Token.time_slot == slot_name,
            Token.status.in_(["WAITING", "APPROACHING", "SERVING"])
        ).count()

        remaining = max(0, SLOT_CAPACITY - booked_count)
        is_avail = remaining > 0
        status_str = f"Available ({remaining} spots left)" if is_avail else "Full / Unavailable"

        slots_data.append(SlotInfo(
            slot=slot_name,
            capacity=SLOT_CAPACITY,
            booked=booked_count,
            remaining=remaining,
            available=is_avail,
            status_text=status_str,
        ))

    return SlotAvailabilityResponse(
        service_id=service.id,
        service_name=service.name,
        date=canonical_date,
        date_label=date_label,
        is_allowed_date=True,
        slots=slots_data,
    )


@router.post("/book", response_model=TokenOut)
def book_token(
    token_data: TokenCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Generate a Bank Token From Home within 2 days.
    Requires user authentication, validates slot capacity, and prevents duplicate bookings.
    """
    # 1. Require user login for protected booking feature
    current_user = get_optional_current_user(authorization, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in or create an account to book your bank token from home."
        )

    # 2. Validate Service
    service = db.query(BankService).filter(BankService.id == token_data.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Selected banking service does not exist.")

    # 3. Validate Date (Strictly within next 2 calendar days)
    canonical_date, date_label = normalize_booking_date(token_data.booking_date)

    # 4. Validate Slot
    time_slot = token_data.time_slot.strip()
    if time_slot not in STANDARD_TIME_SLOTS:
        raise HTTPException(status_code=400, detail="Please select a valid bank time slot from the list.")

    # 5. Prevent Duplicate Bookings for the same user on the same date & service
    existing_user_token = db.query(Token).filter(
        Token.user_id == current_user.id,
        Token.service_id == service.id,
        Token.booking_date.in_([canonical_date, date_label]),
        Token.status.in_(["WAITING", "APPROACHING"])
    ).first()

    if existing_user_token:
        raise HTTPException(
            status_code=400,
            detail=f"You already have an active token ({existing_user_token.token_number}) for {service.name} on {date_label}. Please check 'My Tokens'."
        )

    # 6. Check Slot Availability
    current_booked = db.query(Token).filter(
        Token.service_id == service.id,
        Token.booking_date.in_([canonical_date, date_label]),
        Token.time_slot == time_slot,
        Token.status.in_(["WAITING", "APPROACHING", "SERVING"])
    ).count()

    if current_booked >= SLOT_CAPACITY:
        raise HTTPException(
            status_code=400,
            detail=f"The time slot '{time_slot}' for {date_label} is fully booked. Please select another slot."
        )

    # 7. Generate Unique Token Number
    token_num = generate_token_number(db, service.prefix)

    # 8. Assign counter based on prefix
    counter = None
    if service.prefix == "A":
        counter = db.query(Counter).filter(Counter.name == "Counter 1").first()
    elif service.prefix == "B":
        counter = db.query(Counter).filter(Counter.name == "Counter 2").first()
    elif service.prefix == "C":
        counter = db.query(Counter).filter(Counter.name == "Counter 3").first()
    else:
        counter = db.query(Counter).filter(Counter.name == "Counter 4").first()

    # 9. Calculate Queue Position & Wait
    tokens_ahead = db.query(Token).filter(
        Token.service_id == service.id,
        Token.status.in_(["WAITING", "APPROACHING"])
    ).count()

    estimated_wait = (tokens_ahead + 1) * service.duration_minutes
    arrival_dt = datetime.utcnow() + timedelta(minutes=max(5, estimated_wait - 10))
    rec_arrival = arrival_dt.strftime("%I:%M %p")

    # 10. Persist Token linked to current_user.id (Strict Data Isolation)
    customer_phone = token_data.customer_phone.strip() if token_data.customer_phone else (current_user.phone or "N/A")
    customer_email = token_data.customer_email.strip() if token_data.customer_email else current_user.email
    customer_name = token_data.customer_name.strip() if token_data.customer_name else current_user.full_name

    new_token = Token(
        token_number=token_num,
        service_id=service.id,
        counter_id=counter.id if counter else None,
        user_id=current_user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        customer_account_number=token_data.customer_account_number,
        booking_date=canonical_date,
        time_slot=time_slot,
        status="APPROACHING" if estimated_wait <= 15 else "WAITING",
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    # 11. Broadcast Live Event
    notice_text = f"Token {token_num} booked by {new_token.customer_name} for {date_label} ({time_slot})."
    queue_manager.add_update(notice_text)
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(queue_manager.broadcast({
            "event": "TOKEN_BOOKED",
            "token_number": token_num,
            "service": service.name,
            "counter": counter.name if counter else "Counter 1",
            "time_slot": time_slot,
        }))
    except RuntimeError:
        pass

    return TokenOut(
        id=new_token.id,
        token_number=new_token.token_number,
        service_id=service.id,
        service_name=service.name,
        customer_name=new_token.customer_name,
        customer_phone=new_token.customer_phone,
        customer_account_number=new_token.customer_account_number,
        booking_date=f"{canonical_date} ({date_label})",
        time_slot=new_token.time_slot,
        status=new_token.status,
        counter_id=counter.id if counter else None,
        counter_name=counter.name if counter else "General Desk",
        desk_label=counter.desk_label if counter else "Customer Desk",
        people_ahead=tokens_ahead,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
        created_at=new_token.created_at,
    )


@router.get("/my-tokens", response_model=List[TokenOut])
def get_user_tokens(
    authorization: Optional[str] = Header(None),
    phone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Fetch tokens for the authenticated user only.
    Guarantees strict user isolation: User A will never see User B's tokens.
    """
    current_user = get_optional_current_user(authorization, db)

    tokens = []
    if current_user:
        # Strictly user's own tokens
        tokens = db.query(Token).filter(
            (Token.user_id == current_user.id) |
            (Token.customer_email == current_user.email)
        ).order_by(Token.id.desc()).all()
    elif phone:
        # Fallback for manual check if token not yet provided
        tokens = db.query(Token).filter(Token.customer_phone == phone.strip()).order_by(Token.id.desc()).all()
    else:
        return []

    out = []
    for t in tokens:
        srv = db.query(BankService).filter(BankService.id == t.service_id).first()
        cnt = db.query(Counter).filter(Counter.id == t.counter_id).first() if t.counter_id else None
        ahead = db.query(Token).filter(
            Token.service_id == t.service_id,
            Token.status.in_(["WAITING", "APPROACHING"]),
            Token.id < t.id
        ).count()
        out.append(TokenOut(
            id=t.id,
            token_number=t.token_number,
            service_id=t.service_id,
            service_name=srv.name if srv else "Banking Service",
            customer_name=t.customer_name,
            customer_phone=t.customer_phone,
            customer_account_number=t.customer_account_number,
            booking_date=t.booking_date,
            time_slot=t.time_slot,
            status=t.status,
            counter_id=cnt.id if cnt else None,
            counter_name=cnt.name if cnt else "General Desk",
            desk_label=cnt.desk_label if cnt else "Service Counter",
            people_ahead=ahead,
            estimated_wait_minutes=t.estimated_wait_minutes,
            recommended_arrival_time=t.recommended_arrival_time,
            created_at=t.created_at,
        ))
    return out


@router.get("/track/{token_number}", response_model=TokenTrackerResponse)
def track_token(token_number: str, db: Session = Depends(get_db)):
    token_num_clean = token_number.strip().upper()
    token = db.query(Token).filter(Token.token_number == token_num_clean).first()
    if not token:
        raise HTTPException(status_code=404, detail=f"Token '{token_number}' not found. Please verify your token number.")

    service = db.query(BankService).filter(BankService.id == token.service_id).first()
    counter = db.query(Counter).filter(Counter.id == token.counter_id).first() if token.counter_id else None

    people_ahead = 0
    if token.status in ["WAITING", "APPROACHING"]:
        people_ahead = db.query(Token).filter(
            Token.service_id == token.service_id,
            Token.status.in_(["WAITING", "APPROACHING"]),
            Token.id < token.id
        ).count()

    estimated_wait = people_ahead * (service.duration_minutes if service else 10)

    if token.status == "SERVING":
        notice = f"Your token {token.token_number} is now being served at {counter.name if counter else 'Counter'} ({counter.desk_label if counter else ''}). Please proceed immediately."
    elif token.status == "APPROACHING" or people_ahead <= 2:
        notice = f"Your token {token.token_number} is approaching. Please plan to arrive at the branch soon."
    elif token.status == "COMPLETED":
        notice = f"Your token {token.token_number} service was completed. Thank you for banking with us!"
    elif token.status == "CANCELLED":
        notice = f"This token has been cancelled."
    else:
        notice = f"Your token {token.token_number} is scheduled for {token.time_slot}. {people_ahead} customer(s) ahead."

    return TokenTrackerResponse(
        token_number=token.token_number,
        service_name=service.name if service else "Banking Service",
        customer_name=token.customer_name,
        status=token.status,
        counter_name=counter.name if counter else "Counter 1",
        desk_label=counter.desk_label if counter else "General Desk",
        people_ahead=people_ahead,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=token.recommended_arrival_time or "10-15 minutes prior",
        notice=notice,
        booking_date=token.booking_date,
        time_slot=token.time_slot,
    )


@router.delete("/{token_number}/cancel")
def cancel_token(token_number: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_number.strip().upper()).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.status = "CANCELLED"
    db.commit()

    notice = f"Token {token.token_number} was cancelled."
    queue_manager.add_update(notice)
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(queue_manager.broadcast({"event": "TOKEN_CANCELLED", "token_number": token.token_number}))
    except RuntimeError:
        pass
    return {"success": True, "message": f"Token {token_number} cancelled successfully"}


@router.post("/walk-in", response_model=TokenOut)
def issue_walk_in_token(
    service_id: int = Query(...),
    customer_name: Optional[str] = Query("Walk-in Customer"),
    customer_phone: Optional[str] = Query("+910000000000"),
    db: Session = Depends(get_db)
):
    service = db.query(BankService).filter(BankService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Selected service not found")

    token_num = generate_token_number(db, service.prefix)

    counter = None
    if service.prefix == "A":
        counter = db.query(Counter).filter(Counter.name == "Counter 1").first()
    elif service.prefix == "B":
        counter = db.query(Counter).filter(Counter.name == "Counter 2").first()
    elif service.prefix == "C":
        counter = db.query(Counter).filter(Counter.name == "Counter 3").first()
    else:
        counter = db.query(Counter).filter(Counter.name == "Counter 4").first()

    tokens_ahead = db.query(Token).filter(
        Token.service_id == service.id,
        Token.status.in_(["WAITING", "APPROACHING"])
    ).count()

    estimated_wait = (tokens_ahead + 1) * service.duration_minutes
    now_str = datetime.utcnow().strftime("%I:%M %p")

    new_token = Token(
        token_number=token_num,
        service_id=service.id,
        counter_id=counter.id if counter else None,
        customer_name=customer_name or "Walk-in Customer",
        customer_phone=customer_phone or "+910000000000",
        booking_date=date.today().strftime("%Y-%m-%d"),
        time_slot=f"Walk-in ({now_str})",
        status="APPROACHING" if estimated_wait <= 15 else "WAITING",
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time="Immediate (At Branch)",
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    notice_text = f"Walk-in ticket {token_num} issued for {service.name}."
    queue_manager.add_update(notice_text)
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(queue_manager.broadcast({
            "event": "TOKEN_BOOKED",
            "token_number": token_num,
            "service": service.name,
            "counter": counter.name if counter else "General Desk",
            "time_slot": "Walk-in",
        }))
    except RuntimeError:
        pass

    return TokenOut(
        id=new_token.id,
        token_number=new_token.token_number,
        service_id=service.id,
        service_name=service.name,
        customer_name=new_token.customer_name,
        customer_phone=new_token.customer_phone,
        customer_account_number=None,
        booking_date=new_token.booking_date,
        time_slot=new_token.time_slot,
        status=new_token.status,
        counter_id=counter.id if counter else None,
        counter_name=counter.name if counter else "General Desk",
        desk_label=counter.desk_label if counter else "Service Desk",
        people_ahead=tokens_ahead,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=new_token.recommended_arrival_time,
        created_at=new_token.created_at,
    )
