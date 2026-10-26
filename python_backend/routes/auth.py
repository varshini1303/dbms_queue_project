import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, AuthResponse, UserOut
from auth import hash_password, verify_password, create_access_token, verify_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in or register to access this feature."
        )
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again."
        )
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    return user


def get_optional_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub", 0))
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


@router.post("/register", response_model=AuthResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # 1. Validate full name
    name = user_data.full_name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Please enter your full name (at least 2 characters).")

    # 2. Validate email
    email = user_data.email.strip().lower()
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # 3. Validate password
    password = user_data.password
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # 4. Validate confirm password (if provided)
    if user_data.confirm_password is not None:
        if password != user_data.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match. Please re-enter your password.")

    # 5. Check if email already registered
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="An account with this email address already exists. Please sign in.")

    # 6. Optional phone handling (generate unique placeholder if omitted for DB NOT NULL/UNIQUE compatibility)
    import uuid
    phone = user_data.phone.strip() if user_data.phone else f"acc_{uuid.uuid4().hex[:12]}"
    if user_data.phone:
        phone_match = db.query(User).filter(User.phone == phone).first()
        if phone_match:
            phone = f"acc_{uuid.uuid4().hex[:12]}"

    # 7. Create new user
    new_user = User(
        full_name=name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role="CUSTOMER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 8. Generate JWT access token
    token = create_access_token(new_user.id, new_user.email, new_user.role)
    return AuthResponse(access_token=token, user=UserOut.from_orm(new_user))


@router.post("/login", response_model=AuthResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Accept either email or identifier field
    ident = (login_data.email or login_data.identifier or "").strip().lower()
    password = login_data.password

    if not ident:
        raise HTTPException(status_code=400, detail="Email is required.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    # Look up user by email or phone
    user = db.query(User).filter((User.email == ident) | (User.phone == ident)).first()
    if not user or not verify_password(user.password_hash, password):
        raise HTTPException(status_code=400, detail="Invalid email or password. Please verify your credentials.")

    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(access_token=token, user=UserOut.from_orm(user))


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return UserOut.from_orm(current_user)
