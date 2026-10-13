from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from models import Token, Counter, BankService
from schemas import LiveQueueResponse, CounterOut, LiveQueueUpdate
from queue_manager import queue_manager

router = APIRouter(prefix="/api/v1/queue", tags=["Live Queue"])


@router.get("/live", response_model=LiveQueueResponse)
def get_live_queue(db: Session = Depends(get_db)):
    """Fetch complete live queue status matching the BankQueue live page."""
    total_waiting = db.query(Token).filter(Token.status.in_(["WAITING", "APPROACHING"])).count()
    total_served = db.query(Token).filter(Token.status == "COMPLETED").count()
    active_counters = db.query(Counter).filter(Counter.status.in_(["ONLINE", "BUSY"])).count()

    counters = db.query(Counter).all()
    counter_outs = []
    now_serving = []

    for c in counters:
        curr_token = None
        if c.current_token_id:
            curr = db.query(Token).filter(Token.id == c.current_token_id).first()
            if curr and curr.status == "SERVING":
                curr_token = curr.token_number
                srv = db.query(BankService).filter(BankService.id == curr.service_id).first()
                now_serving.append({
                    "token_number": curr.token_number,
                    "customer_name": curr.customer_name,
                    "counter_name": c.name,
                    "desk_label": c.desk_label,
                    "service_name": srv.name if srv else "Service",
                    "time_slot": curr.time_slot,
                })

        waiting_count = db.query(Token).filter(
            Token.counter_id == c.id,
            Token.status.in_(["WAITING", "APPROACHING"])
        ).count()

        counter_outs.append(CounterOut(
            id=c.id,
            name=c.name,
            desk_label=c.desk_label,
            description=c.description,
            status=c.status,
            staff_name=c.staff_name,
            current_token_number=curr_token,
            waiting_count=waiting_count,
        ))

    # Upcoming tokens
    upcoming = db.query(Token).filter(
        Token.status.in_(["WAITING", "APPROACHING"])
    ).order_by(Token.id.asc()).limit(8).all()

    upcoming_list = []
    for t in upcoming:
        srv = db.query(BankService).filter(BankService.id == t.service_id).first()
        cnt = db.query(Counter).filter(Counter.id == t.counter_id).first() if t.counter_id else None
        upcoming_list.append({
            "token_number": t.token_number,
            "customer_name": t.customer_name,
            "service_name": srv.name if srv else "Service",
            "counter_name": cnt.name if cnt else "Assigned Counter",
            "status": t.status,
            "estimated_wait_minutes": t.estimated_wait_minutes,
            "recommended_arrival_time": t.recommended_arrival_time,
            "time_slot": t.time_slot,
        })

    avg_wait = 12 if total_waiting > 0 else 5

    return LiveQueueResponse(
        total_waiting=total_waiting,
        total_served_today=total_served,
        active_counters_count=active_counters,
        average_wait_minutes=avg_wait,
        counters=counter_outs,
        now_serving=now_serving,
        upcoming_tokens=upcoming_list,
        recent_updates=[LiveQueueUpdate(**u) for u in queue_manager.recent_updates],
    )


@router.get("/manage-tokens")
def get_all_manage_tokens(db: Session = Depends(get_db)):
    """List all tokens across today for admin/staff control panel."""
    tokens = db.query(Token).order_by(Token.id.desc()).limit(50).all()
    results = []
    for t in tokens:
        srv = db.query(BankService).filter(BankService.id == t.service_id).first()
        cnt = db.query(Counter).filter(Counter.id == t.counter_id).first() if t.counter_id else None
        results.append({
            "id": t.id,
            "token_number": t.token_number,
            "customer_name": t.customer_name,
            "customer_phone": t.customer_phone,
            "service_name": srv.name if srv else "Unknown",
            "counter_name": cnt.name if cnt else "Unassigned",
            "time_slot": t.time_slot,
            "booking_date": t.booking_date,
            "status": t.status,
            "estimated_wait_minutes": t.estimated_wait_minutes,
            "created_at": t.created_at.strftime("%I:%M %p") if t.created_at else "-",
        })
    return results


@router.websocket("/ws")
async def websocket_queue_endpoint(websocket: WebSocket):
    """Real-time live queue WebSocket connection."""
    await queue_manager.connect(websocket)
    try:
        while True:
            # Keep-alive or client queries
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        queue_manager.disconnect(websocket)
