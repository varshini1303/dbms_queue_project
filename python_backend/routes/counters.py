from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Counter, Token, BankService
from schemas import CounterOut
from queue_manager import queue_manager

router = APIRouter(prefix="/api/v1/counters", tags=["Counters"])


@router.get("", response_model=List[CounterOut])
def get_counters(db: Session = Depends(get_db)):
    counters = db.query(Counter).all()
    out = []
    for c in counters:
        current_token_num = None
        if c.current_token_id:
            curr = db.query(Token).filter(Token.id == c.current_token_id).first()
            if curr and curr.status == "SERVING":
                current_token_num = curr.token_number

        waiting_count = db.query(Token).filter(
            Token.counter_id == c.id,
            Token.status.in_(["WAITING", "APPROACHING"])
        ).count()

        out.append(CounterOut(
            id=c.id,
            name=c.name,
            desk_label=c.desk_label,
            description=c.description,
            status=c.status,
            staff_name=c.staff_name,
            current_token_number=current_token_num,
            waiting_count=waiting_count,
        ))
    return out


@router.post("/{counter_id}/call-next")
async def call_next_token(counter_id: int, db: Session = Depends(get_db)):
    """Counter staff calls the next waiting token."""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter:
        raise HTTPException(status_code=404, detail="Counter not found")

    # Complete current token if still serving
    if counter.current_token_id:
        prev_token = db.query(Token).filter(Token.id == counter.current_token_id).first()
        if prev_token and prev_token.status == "SERVING":
            prev_token.status = "COMPLETED"
            prev_token.completed_at = datetime.utcnow()

    # Find next token waiting for this counter (or matching its prefix)
    next_token = db.query(Token).filter(
        Token.counter_id == counter.id,
        Token.status.in_(["WAITING", "APPROACHING"])
    ).order_by(Token.id.asc()).first()

    if not next_token:
        # Check any unassigned waiting token
        next_token = db.query(Token).filter(
            Token.status.in_(["WAITING", "APPROACHING"])
        ).order_by(Token.id.asc()).first()

    if not next_token:
        counter.current_token_id = None
        db.commit()
        return {"success": True, "message": f"{counter.name} is now idle (no waiting tokens)", "token": None}

    next_token.status = "SERVING"
    next_token.counter_id = counter.id
    next_token.called_at = datetime.utcnow()
    counter.current_token_id = next_token.id
    counter.status = "BUSY"
    db.commit()

    # Update upcoming tokens to APPROACHING if they are next
    upcoming = db.query(Token).filter(
        Token.counter_id == counter.id,
        Token.status == "WAITING"
    ).order_by(Token.id.asc()).first()
    if upcoming:
        upcoming.status = "APPROACHING"
        db.commit()
        notice_approaching = f"Your token {upcoming.token_number} is approaching. Please plan to arrive soon."
        queue_manager.add_update(notice_approaching)

    notice = f"Token {next_token.token_number} is now being served at {counter.name} ({counter.desk_label})."
    queue_manager.add_update(notice)
    await queue_manager.broadcast({
        "event": "TOKEN_CALLED",
        "counter_id": counter.id,
        "counter_name": counter.name,
        "token_number": next_token.token_number,
        "customer_name": next_token.customer_name,
    })

    return {
        "success": True,
        "message": notice,
        "token_number": next_token.token_number,
        "customer_name": next_token.customer_name,
        "counter": counter.name,
    }


@router.post("/{counter_id}/complete")
async def complete_current_token(counter_id: int, db: Session = Depends(get_db)):
    """Mark token serving at this counter as completed."""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter:
        raise HTTPException(status_code=404, detail="Counter not found")

    if not counter.current_token_id:
        return {"success": True, "message": f"{counter.name} has no active token"}

    token = db.query(Token).filter(Token.id == counter.current_token_id).first()
    if token:
        token.status = "COMPLETED"
        token.completed_at = datetime.utcnow()

    counter.current_token_id = None
    counter.status = "ONLINE"
    db.commit()

    if token:
        notice = f"Token {token.token_number} completed service at {counter.name}."
        queue_manager.add_update(notice)
        await queue_manager.broadcast({
            "event": "TOKEN_COMPLETED",
            "token_number": token.token_number,
            "counter_name": counter.name,
        })

    return {"success": True, "message": f"Token completed at {counter.name}"}


@router.post("/{counter_id}/status")
def set_counter_status(counter_id: int, status: str, db: Session = Depends(get_db)):
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter:
        raise HTTPException(status_code=404, detail="Counter not found")
    counter.status = status.upper()
    db.commit()
    return {"success": True, "counter": counter.name, "status": counter.status}


@router.post("/{counter_id}/recall")
async def recall_current_token(counter_id: int, db: Session = Depends(get_db)):
    """Re-announce/recall current token at counter."""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter or not counter.current_token_id:
        raise HTTPException(status_code=400, detail="Counter has no active token to recall")

    token = db.query(Token).filter(Token.id == counter.current_token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Active token not found")

    notice = f"Reminder: Token {token.token_number} please report to {counter.name} ({counter.desk_label})."
    queue_manager.add_update(notice)
    await queue_manager.broadcast({
        "event": "TOKEN_RECALLED",
        "counter_name": counter.name,
        "desk_label": counter.desk_label,
        "token_number": token.token_number,
        "customer_name": token.customer_name,
    })
    return {"success": True, "message": notice}


@router.post("/{counter_id}/skip")
async def skip_current_token(counter_id: int, db: Session = Depends(get_db)):
    """Mark current customer as NO_SHOW if absent."""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter or not counter.current_token_id:
        raise HTTPException(status_code=400, detail="Counter has no active token to skip")

    token = db.query(Token).filter(Token.id == counter.current_token_id).first()
    if token:
        token.status = "NO_SHOW"
        token.completed_at = datetime.utcnow()

    counter.current_token_id = None
    counter.status = "ONLINE"
    db.commit()

    notice = f"Token {token.token_number} was marked as No-Show at {counter.name}."
    queue_manager.add_update(notice)
    await queue_manager.broadcast({
        "event": "TOKEN_SKIPPED",
        "counter_name": counter.name,
        "token_number": token.token_number,
    })
    return {"success": True, "message": notice}
