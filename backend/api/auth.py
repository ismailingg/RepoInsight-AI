import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.db.connection import get_db
from backend.db.models import User, RepoSession
from backend.utils.auth import hash_password, verify_password, create_token, get_current_user
from backend.utils.mailer import send_verification_email

router = APIRouter(prefix="/auth", tags=["Auth"])

PENDING_EXPIRE_HOURS  = 24


# ── Request / Response models ───────────────────────────────────

class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class AuthResponse(BaseModel):
    token:   str
    user_id: str
    email:   str
    message: str


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(422, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        if existing.is_verified:
            raise HTTPException(409, detail="An account with this email already exists")
        else:
            # Resend verification for unverified account
            token                      = secrets.token_urlsafe(32)
            existing.verification_token = token
            existing.token_expires_at   = datetime.utcnow() + timedelta(hours=PENDING_EXPIRE_HOURS)
            db.commit()
            try:
                send_verification_email(existing.email, token)
            except Exception as e:
                raise HTTPException(500, detail=f"Could not send verification email: {e}")
            return {"message": "Verification email resent. Check your inbox.", "email": existing.email}

    token      = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=PENDING_EXPIRE_HOURS)

    user = User(
        email               = req.email,
        password_hash       = hash_password(req.password),
        is_verified         = False,
        verification_token  = token,
        token_expires_at    = expires_at
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        send_verification_email(req.email, token)
    except Exception as e:
        db.delete(user)
        db.commit()
        raise HTTPException(500, detail=f"Could not send verification email: {e}. Check SMTP settings in .env")

    return {
        "message": "Check your email to verify your account before logging in.",
        "email":   req.email
    }


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(400, detail="Invalid or already-used verification link.")

    if user.token_expires_at and datetime.utcnow() > user.token_expires_at:
        raise HTTPException(400, detail="Verification link has expired. Please register again.")

    user.is_verified        = True
    user.verification_token = None
    user.token_expires_at   = None
    db.commit()

    jwt_token = create_token(str(user.id))
    return AuthResponse(
        token   = jwt_token,
        user_id = str(user.id),
        email   = user.email,
        message = "Email verified! Your account is ready."
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(403, detail="EMAIL_NOT_VERIFIED")

    return AuthResponse(
        token   = create_token(str(user.id)),
        user_id = str(user.id),
        email   = user.email,
        message = "Login successful"
    )


@router.post("/resend-verification")
def resend_verification(req: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, detail="Invalid email or password")

    if user.is_verified:
        raise HTTPException(400, detail="This account is already verified")

    token                    = secrets.token_urlsafe(32)
    user.verification_token  = token
    user.token_expires_at    = datetime.utcnow() + timedelta(hours=PENDING_EXPIRE_HOURS)
    db.commit()

    try:
        send_verification_email(req.email, token)
    except Exception as e:
        raise HTTPException(500, detail=f"Could not send email: {e}")

    return {"message": "Verification email resent. Check your inbox."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id":    str(current_user.id),
        "email":      current_user.email,
        "created_at": current_user.created_at.isoformat()
    }


@router.delete("/account")
def delete_account(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Permanently delete the user's account.
    Cascades automatically to api_keys and repo_sessions (via SQLAlchemy cascade).
    Also deletes all ChromaDB vector collections for this user's repos.
    """
    import hashlib
    import chromadb
    from backend.config import CHROMA_DB_PATH

    # Delete ChromaDB collections first
    try:
        chroma   = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        sessions = db.query(RepoSession).filter(
            RepoSession.user_id == current_user.id
        ).all()
        for s in sessions:
            try:
                combined  = f"{str(current_user.id)}:{s.repo_url}"
                repo_hash = hashlib.md5(combined.encode()).hexdigest()[:16]
                chroma.delete_collection(f"repo_{repo_hash}")
                print(f"[DELETE ACCOUNT] Removed collection repo_{repo_hash}")
            except Exception as e:
                print(f"[DELETE ACCOUNT] Chroma warning for {s.repo_url}: {e}")
    except Exception as e:
        print(f"[DELETE ACCOUNT] Chroma client error: {e}")

    # Delete user row — cascade removes api_keys + repo_sessions
    db.delete(current_user)
    db.commit()

    return {"message": "Account permanently deleted"}