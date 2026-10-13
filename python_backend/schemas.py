from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class ServiceBase(BaseModel):
    name: str
    description: str
    estimated_time: str
    duration_minutes: int
    prefix: str
    icon: str


class ServiceOut(ServiceBase):
    id: int
    code: str
    is_active: bool

    class Config:
        from_attributes = True


class CounterOut(BaseModel):
    id: int
    name: str
    desk_label: str
    description: str
    status: str
    staff_name: str
    current_token_number: Optional[str] = None
    waiting_count: int = 0

    class Config:
        from_attributes = True


class TokenCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    customer_account_number: Optional[str] = None
    service_id: int
    booking_date: str  # "Today", "Tomorrow", or YYYY-MM-DD
    time_slot: str     # "10:30 AM" or "Morning (9:00 AM - 11:00 AM)"


class TokenOut(BaseModel):
    id: int
    token_number: str
    service_id: int
    service_name: str
    customer_name: str
    customer_phone: str
    customer_account_number: Optional[str] = None
    booking_date: str
    time_slot: str
    status: str
    counter_id: Optional[int] = None
    counter_name: Optional[str] = None
    desk_label: Optional[str] = None
    people_ahead: int
    estimated_wait_minutes: int
    recommended_arrival_time: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenTrackerResponse(BaseModel):
    token_number: str
    service_name: str
    customer_name: str
    status: str  # WAITING, APPROACHING, SERVING, COMPLETED, CANCELLED
    counter_name: Optional[str] = None
    desk_label: Optional[str] = None
    people_ahead: int
    estimated_wait_minutes: int
    recommended_arrival_time: str
    notice: str
    booking_date: str
    time_slot: str


class LiveQueueUpdate(BaseModel):
    id: str
    text: str
    timestamp: str


class LiveQueueResponse(BaseModel):
    total_waiting: int
    total_served_today: int
    active_counters_count: int
    average_wait_minutes: int
    counters: List[CounterOut]
    now_serving: List[dict]
    upcoming_tokens: List[dict]
    recent_updates: List[LiveQueueUpdate]


class UserRegister(BaseModel):
    full_name: str
    phone: str
    email: str
    password: str


class UserLogin(BaseModel):
    identifier: str  # Email or Phone
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    phone: str
    email: str
    role: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ContactCreate(BaseModel):
    name: str
    email: str
    message: str


class ContactResponse(BaseModel):
    success: bool
    message: str
