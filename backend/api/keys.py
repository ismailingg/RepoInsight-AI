from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.db.connection import get_db
from backend.db.models import User, ApiKey
from backend.utils.auth import get_current_user
from backend.utils.crypto import encrypt_key, decrypt_key

router = APIRouter(prefix="/keys", tags=["API Keys"])


# ── Request / Response models ───────────────────────────────────

class SaveKeyRequest(BaseModel):
    provider:   str            # google / openai / groq / openrouter / anthropic
    key_type:   str            # embedding / llm
    api_key:    str            # plaintext — encrypted before storage
    model_name: Optional[str] = None


class KeyResponse(BaseModel):
    provider:   str
    key_type:   str
    model_name: Optional[str]
    exists:     bool           # true — never returns the actual key


class KeysResponse(BaseModel):
    keys: List[KeyResponse]


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
def save_key(
    req:          SaveKeyRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Save or update an API key for a provider.
    Key is AES-256 encrypted before storage — plaintext never hits the DB.
    If a key already exists for this provider+type, it gets overwritten.
    """
    # Validate provider
    valid_providers = {"google", "openai", "groq", "openrouter", "anthropic"}
    if req.provider not in valid_providers:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider. Must be one of: {valid_providers}"
        )

    # Validate key_type
    valid_types = {"embedding", "llm"}
    if req.key_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid key_type. Must be one of: {valid_types}"
        )

    # Encrypt before storing
    encrypted = encrypt_key(req.api_key)

    # Upsert — update if exists, insert if not
    existing = db.query(ApiKey).filter(
        ApiKey.user_id  == current_user.id,
        ApiKey.provider == req.provider,
        ApiKey.key_type == req.key_type
    ).first()

    if existing:
        existing.encrypted_key = encrypted
        existing.model_name    = req.model_name
    else:
        new_key = ApiKey(
            user_id       = current_user.id,
            provider      = req.provider,
            key_type      = req.key_type,
            encrypted_key = encrypted,
            model_name    = req.model_name
        )
        db.add(new_key)

    db.commit()

    return {
        "message":  f"{req.provider} {req.key_type} key saved successfully",
        "provider": req.provider,
        "key_type": req.key_type
    }


@router.get("/", response_model=KeysResponse)
def list_keys(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    List all saved keys for the current user.
    Returns provider + type + model only — never the actual key.
    """
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()

    return KeysResponse(keys=[
        KeyResponse(
            provider   = k.provider,
            key_type   = k.key_type,
            model_name = k.model_name,
            exists     = True
        )
        for k in keys
    ])


@router.delete("/{provider}/{key_type}")
def delete_key(
    provider:     str,
    key_type:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Delete a specific API key.
    Example: DELETE /keys/google/embedding
    """
    key = db.query(ApiKey).filter(
        ApiKey.user_id  == current_user.id,
        ApiKey.provider == provider,
        ApiKey.key_type == key_type
    ).first()

    if not key:
        raise HTTPException(
            status_code=404,
            detail=f"No {provider} {key_type} key found"
        )

    db.delete(key)
    db.commit()

    return {"message": f"{provider} {key_type} key deleted"}


# ── Internal helper (used by ingest + query endpoints) ──────────

def get_user_keys(user_id, db: Session) -> dict:
    """
    Load and decrypt all API keys for a user.
    Returns a dict ready to pass to LLM/embedding functions.

    Example return:
    {
        "embedding_provider": "google",
        "embedding_key":      "AIzaSy...",
        "embedding_model":    "models/gemini-embedding-001",
        "llm_provider":       "openrouter",
        "llm_key":            "sk-or-...",
        "llm_model":          "google/gemini-2.0-flash-exp:free"
    }
    """
    keys = db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

    result = {}
    for k in keys:
        decrypted = decrypt_key(k.encrypted_key)
        if k.key_type == "embedding":
            result["embedding_provider"] = k.provider
            result["embedding_key"]      = decrypted
            result["embedding_model"]    = k.model_name
        elif k.key_type == "llm":
            result["llm_provider"] = k.provider
            result["llm_key"]      = decrypted
            result["llm_model"]    = k.model_name

    return result