from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, AuthResponse, UserOut
from auth import hash_password, verify_password, create_access_token, verify_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication token")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired or invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/register", response_model=AuthResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check duplicate phone or email
    if db.query(User).filter((User.email == user_data.email) | (User.phone == user_data.phone)).first():
        raise HTTPException(status_code=400, detail="User with this email or phone number already exists")

    new_user = User(
        full_name=user_data.full_name,
        phone=user_data.phone,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="CUSTOMER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.id, new_user.email, new_user.role)
    return AuthResponse(access_token=token, user=UserOut.from_orm(new_user))


@router.post("/login", response_model=AuthResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    ident = login_data.identifier.strip()
    user = db.query(User).filter((User.email == ident) | (User.phone == ident)).first()
    if not user or not verify_password(user.password_hash, login_data.password):
        raise HTTPException(status_code=400, detail="Invalid phone/email or password")

    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(access_token=token, user=UserOut.from_orm(user))


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return UserOut.from_orm(current_user)
