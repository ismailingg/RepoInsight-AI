from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.db.connection import get_db
from backend.db.models import User
from backend.utils.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Request / Response models ───────────────────────────────────

class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AuthResponse(BaseModel):
    token:      str
    user_id:    str
    email:      str
    message:    str


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.
    Returns a JWT token immediately — no need to login after registering.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )

    # Validate password length
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )

    # Create user — password hashed, never stored as plaintext
    user = User(
        email         = req.email,
        password_hash = hash_password(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return token immediately
    token = create_token(str(user.id))

    return AuthResponse(
        token   = token,
        user_id = str(user.id),
        email   = user.email,
        message = "Account created successfully"
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns a JWT token valid for 7 days.
    """
    # Find user
    user = db.query(User).filter(User.email == req.email).first()

    # Intentionally vague error — don't reveal if email exists
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_token(str(user.id))

    return AuthResponse(
        token   = token,
        user_id = str(user.id),
        email   = user.email,
        message = "Login successful"
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return current user info.
    Frontend calls this on app load to verify token + get user details.
    """
    return {
        "user_id":    str(current_user.id),
        "email":      current_user.email,
        "created_at": current_user.created_at.isoformat()
    }