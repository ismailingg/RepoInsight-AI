import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.db.connection import get_db
from backend.db.models import User
from backend.utils.auth import hash_password, verify_password, create_token, get_current_user
from backend.utils.mailer import send_verification_email

router = APIRouter(prefix="/auth", tags=["Auth"])

VERIFY_TOKEN_EXPIRE_HOURS = 24


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

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.
    Sends a verification email — does NOT return a JWT token yet.
    The user must verify their email before they can log in.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        if existing.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )
        else:
            # Account exists but unverified — resend verification email
            token            = secrets.token_urlsafe(32)
            existing.verification_token = token
            existing.token_expires_at   = datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)
            db.commit()
            try:
                send_verification_email(existing.email, token)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Could not send verification email: {e}"
                )
            return {
                "message": "Verification email resent. Please check your inbox.",
                "email":   existing.email
            }

    # Validate password length
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )

    # Generate verification token
    token      = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)

    # Create user — unverified until email confirmed
    user = User(
        email              = req.email,
        password_hash      = hash_password(req.password),
        is_verified        = False,
        verification_token = token,
        token_expires_at   = expires_at
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    try:
        send_verification_email(req.email, token)
    except Exception as e:
        # Delete the user so they can try again
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Account created but verification email failed: {e}. "
                   f"Check SMTP_EMAIL and SMTP_PASSWORD in your .env file."
        )

    return {
        "message": "Account created! Check your email to verify your account before logging in.",
        "email":   req.email
    }


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify a user's email address using the token from the email link.
    Called by the frontend when it detects ?verify=<token> in the URL.
    Returns a JWT token so the user is logged in immediately after verifying.
    """
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification link. It may have already been used."
        )

    if user.token_expires_at and datetime.utcnow() > user.token_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Verification link has expired. Please register again to get a new link."
        )

    # Mark as verified, clear the token
    user.is_verified        = True
    user.verification_token = None
    user.token_expires_at   = None
    db.commit()

    # Return JWT so they're logged in immediately
    jwt_token = create_token(str(user.id))
    return AuthResponse(
        token   = jwt_token,
        user_id = str(user.id),
        email   = user.email,
        message = "Email verified! You are now logged in."
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns a JWT token valid for 7 days.
    Blocks login if email is not verified.
    """
    user = db.query(User).filter(User.email == req.email).first()

    # Intentionally vague for non-existent users to prevent enumeration
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Specific message for unverified users
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED"
        )

    token = create_token(str(user.id))

    return AuthResponse(
        token   = token,
        user_id = str(user.id),
        email   = user.email,
        message = "Login successful"
    )


@router.post("/resend-verification")
def resend_verification(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Resend verification email. Requires email + password to prevent abuse.
    """
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="This account is already verified")

    token                    = secrets.token_urlsafe(32)
    user.verification_token  = token
    user.token_expires_at    = datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS)
    db.commit()

    try:
        send_verification_email(req.email, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not send email: {e}")

    return {"message": "Verification email resent. Check your inbox."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return current user info.
    Frontend calls this on app load to verify token + get user details.
    """
    return {
        "user_id":     str(current_user.id),
        "email":       current_user.email,
        "is_verified": current_user.is_verified,
        "created_at":  current_user.created_at.isoformat()
    }