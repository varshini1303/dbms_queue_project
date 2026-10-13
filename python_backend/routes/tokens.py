import random
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Token, BankService, Counter, User
from schemas import TokenCreate, TokenOut, TokenTrackerResponse
from queue_manager import queue_manager

router = APIRouter(prefix="/api/v1/tokens", tags=["Tokens"])


def generate_token_number(db: Session, prefix: str) -> str:
    # Find highest current token number for today
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
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


def calculate_queue_position_and_wait(db: Session, service: BankService, token: Token):
    # Find counter assigned to this service prefix
    counter = db.query(Counter).filter(Counter.status != "OFFLINE").first()
    # Find all waiting tokens ahead for this service category
    tokens_ahead = db.query(Token).filter(
        Token.service_id == service.id,
        Token.status.in_(["WAITING", "APPROACHING"]),
        Token.id < token.id
    ).count()

    wait_mins = tokens_ahead * service.duration_minutes
    now = datetime.utcnow()
    # Recommended arrival time = now + wait_mins - 10 min buffer (minimum now)
    arrival_time = now + timedelta(minutes=max(0, wait_mins - 10))
    arrival_str = arrival_time.strftime("%I:%M %p")

    return tokens_ahead, wait_mins, arrival_str


@router.post("/book", response_model=TokenOut)
async def book_token(token_data: TokenCreate, db: Session = Depends(get_db)):
    service = db.query(BankService).filter(BankService.id == token_data.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Selected service does not exist")

    # Generate token number
    token_num = generate_token_number(db, service.prefix)

    # Assign appropriate counter based on service
    counter = None
    if service.prefix == "A":
        counter = db.query(Counter).filter(Counter.name == "Counter 1").first()
    elif service.prefix == "B":
        counter = db.query(Counter).filter(Counter.name == "Counter 2").first()
    elif service.prefix == "C":
        counter = db.query(Counter).filter(Counter.name == "Counter 3").first()
    else:
        counter = db.query(Counter).filter(Counter.name == "Counter 4").first()

    # Calculate queue position & wait
    tokens_ahead = db.query(Token).filter(
        Token.service_id == service.id,
        Token.status.in_(["WAITING", "APPROACHING"])
    ).count()

    estimated_wait = (tokens_ahead + 1) * service.duration_minutes
    # recommended arrival time: 10 mins before slot or estimated wait
    arrival_dt = datetime.utcnow() + timedelta(minutes=max(5, estimated_wait - 10))
    rec_arrival = arrival_dt.strftime("%I:%M %p")

    # If wait time is short (under 15 mins), mark as APPROACHING
    initial_status = "APPROACHING" if estimated_wait <= 15 else "WAITING"

    new_token = Token(
        token_number=token_num,
        service_id=service.id,
        counter_id=counter.id if counter else None,
        customer_name=token_data.customer_name,
        customer_phone=token_data.customer_phone,
        customer_email=token_data.customer_email,
        customer_account_number=token_data.customer_account_number,
        booking_date=token_data.booking_date,
        time_slot=token_data.time_slot,
        status=initial_status,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    # Add queue update & broadcast
    notice_text = f"{token_num} was successfully reserved for {token_data.time_slot}."
    queue_manager.add_update(notice_text)
    await queue_manager.broadcast({
        "event": "TOKEN_BOOKED",
        "token_number": token_num,
        "service": service.name,
        "counter": counter.name if counter else "Counter 1",
        "time_slot": token_data.time_slot,
    })

    return TokenOut(
        id=new_token.id,
        token_number=new_token.token_number,
        service_id=service.id,
        service_name=service.name,
        customer_name=new_token.customer_name,
        customer_phone=new_token.customer_phone,
        customer_account_number=new_token.customer_account_number,
        booking_date=new_token.booking_date,
        time_slot=new_token.time_slot,
        status=new_token.status,
        counter_id=counter.id if counter else None,
        counter_name=counter.name if counter else "General Counter",
        desk_label=counter.desk_label if counter else "Service Desk",
        people_ahead=tokens_ahead,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
        created_at=new_token.created_at,
    )


@router.get("/track/{token_number}", response_model=TokenTrackerResponse)
def track_token(token_number: str, db: Session = Depends(get_db)):
    """Check live status of a token, people ahead, and arrival guidance (for /check-token page)."""
    token_num_clean = token_number.strip().upper()
    token = db.query(Token).filter(Token.token_number == token_num_clean).first()
    if not token:
        raise HTTPException(status_code=404, detail=f"Token '{token_number}' not found. Please verify your token number.")

    service = db.query(BankService).filter(BankService.id == token.service_id).first()
    counter = db.query(Counter).filter(Counter.id == token.counter_id).first() if token.counter_id else None

    # Calculate people ahead in this service / counter
    people_ahead = 0
    if token.status in ["WAITING", "APPROACHING"]:
        people_ahead = db.query(Token).filter(
            Token.service_id == token.service_id,
            Token.status.in_(["WAITING", "APPROACHING"]),
            Token.id < token.id
        ).count()

    estimated_wait = people_ahead * (service.duration_minutes if service else 10)

    # Dynamic status advice notice matching website copy
    if token.status == "SERVING":
        notice = f"Your token {token.token_number} is now being served at {counter.name if counter else 'the counter'} ({counter.desk_label if counter else ''}). Please proceed immediately."
    elif token.status == "APPROACHING" or people_ahead <= 2:
        notice = f"Your token {token.token_number} is approaching. Please plan to arrive soon."
    elif token.status == "COMPLETED":
        notice = f"Your token {token.token_number} service was completed. Thank you for banking with us!"
    elif token.status == "CANCELLED":
        notice = f"This token has been cancelled."
    else:
        notice = f"Your token {token.token_number} is scheduled for {token.time_slot}. {people_ahead} customer(s) ahead."

    rec_arrival = token.recommended_arrival_time or "10-15 minutes before slot"

    return TokenTrackerResponse(
        token_number=token.token_number,
        service_name=service.name if service else "Banking Service",
        customer_name=token.customer_name,
        status=token.status,
        counter_name=counter.name if counter else "Counter 1",
        desk_label=counter.desk_label if counter else "General Desk",
        people_ahead=people_ahead,
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
        notice=notice,
        booking_date=token.booking_date,
        time_slot=token.time_slot,
    )


@router.get("/my-tokens", response_model=List[TokenOut])
def get_user_tokens(phone: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Fetch all tokens for a customer by phone number."""
    if not phone:
        return []
    tokens = db.query(Token).filter(Token.customer_phone == phone.strip()).order_by(Token.id.desc()).all()
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
            service_name=srv.name if srv else "Service",
            customer_name=t.customer_name,
            customer_phone=t.customer_phone,
            customer_account_number=t.customer_account_number,
            booking_date=t.booking_date,
            time_slot=t.time_slot,
            status=t.status,
            counter_id=cnt.id if cnt else None,
            counter_name=cnt.name if cnt else None,
            desk_label=cnt.desk_label if cnt else None,
            people_ahead=ahead,
            estimated_wait_minutes=t.estimated_wait_minutes,
            recommended_arrival_time=t.recommended_arrival_time,
            created_at=t.created_at,
        ))
    return out


@router.delete("/{token_number}/cancel")
async def cancel_token(token_number: str, db: Session = Depends(get_db)):
    token = db.query(Token).filter(Token.token_number == token_number.strip().upper()).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.status = "CANCELLED"
    db.commit()

    notice = f"Token {token.token_number} was cancelled."
    queue_manager.add_update(notice)
    await queue_manager.broadcast({"event": "TOKEN_CANCELLED", "token_number": token.token_number})
    return {"success": True, "message": f"Token {token_number} cancelled successfully"}


@router.post("/walk-in", response_model=TokenOut)
async def issue_walk_in_token(service_id: int = Query(...), customer_name: Optional[str] = Query("Walk-in Customer"), customer_phone: Optional[str] = Query("+910000000000"), db: Session = Depends(get_db)):
    """Fast in-person token ticket issuance for walk-in branch visitors."""
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
    rec_arrival = "Immediate (At Branch)"

    new_token = Token(
        token_number=token_num,
        service_id=service.id,
        counter_id=counter.id if counter else None,
        customer_name=customer_name or "Walk-in Customer",
        customer_phone=customer_phone or "+910000000000",
        booking_date="Today",
        time_slot=f"Walk-in ({now_str})",
        status="APPROACHING" if estimated_wait <= 15 else "WAITING",
        estimated_wait_minutes=estimated_wait,
        recommended_arrival_time=rec_arrival,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    notice_text = f"Walk-in ticket {token_num} issued for {service.name}."
    queue_manager.add_update(notice_text)
    await queue_manager.broadcast({
        "event": "TOKEN_BOOKED",
        "token_number": token_num,
        "service": service.name,
        "counter": counter.name if counter else "General Desk",
        "time_slot": "Walk-in",
    })

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
        recommended_arrival_time=rec_arrival,
        created_at=new_token.created_at,
    )
