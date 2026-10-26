from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=False, index=True, nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="CUSTOMER")  # CUSTOMER, STAFF, ADMIN
    created_at = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("Token", back_populates="user")


class BankService(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    estimated_time = Column(String(20), default="10 min")
    duration_minutes = Column(Integer, default=10)
    prefix = Column(String(5), default="A")
    icon = Column(String(50), default="banknote")
    is_active = Column(Boolean, default=True)

    tokens = relationship("Token", back_populates="service")


class Counter(Base):
    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)          # e.g. "Counter 1"
    desk_label = Column(String(100), nullable=False)    # e.g. "Cash Services"
    description = Column(String(255), default="")
    status = Column(String(20), default="ONLINE")      # ONLINE, BUSY, PAUSED, OFFLINE
    staff_name = Column(String(100), default="Staff Member")
    current_token_id = Column(Integer, ForeignKey("tokens.id"), nullable=True)

    current_token = relationship("Token", foreign_keys=[current_token_id], post_update=True)
    tokens_handled = relationship("Token", foreign_keys="[Token.counter_id]", back_populates="counter")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_number = Column(String(20), unique=True, index=True, nullable=False)  # e.g. "A108"
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    counter_id = Column(Integer, ForeignKey("counters.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer_name = Column(String(120), nullable=False)
    customer_phone = Column(String(20), nullable=False, index=True)
    customer_email = Column(String(120), nullable=True)
    customer_account_number = Column(String(50), nullable=True)

    booking_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    time_slot = Column(String(50), nullable=False)     # e.g. "10:30 AM - 11:00 AM"

    status = Column(String(30), default="WAITING", index=True)  # WAITING, APPROACHING, SERVING, COMPLETED, CANCELLED, NO_SHOW
    estimated_wait_minutes = Column(Integer, default=15)
    recommended_arrival_time = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    called_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    service = relationship("BankService", back_populates="tokens")
    counter = relationship("Counter", foreign_keys=[counter_id], back_populates="tokens_handled")
    user = relationship("User", back_populates="tokens")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
