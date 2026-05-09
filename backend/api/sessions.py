from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.db.connection import get_db
from backend.db.models import User, RepoSession
from backend.utils.auth import get_current_user

router = APIRouter(prefix="/repos", tags=["Repo Sessions"])


# ── Request / Response models ───────────────────────────────────

class RepoSummary(BaseModel):
    repo_url:        str
    status:          str
    chunks_count:    int
    files_count:     int
    vectors_count:   int
    ingested_at:     Optional[str]
    collection_name: Optional[str]
    message_count:   int           # how many Q&A exchanges


class ReposResponse(BaseModel):
    repos: List[RepoSummary]


class ChatMessage(BaseModel):
    role:       str            # user / assistant
    content:    str
    sources:    Optional[list] = []
    confidence: Optional[float] = None
    intent:     Optional[str]  = None


class ChatHistoryResponse(BaseModel):
    repo_url:     str
    chat_history: List[dict]


class AppendMessageRequest(BaseModel):
    repo_url: str
    message:  ChatMessage


class ClearChatRequest(BaseModel):
    repo_url: str


# ── Endpoints ───────────────────────────────────────────────────

@router.get("/", response_model=ReposResponse)
def list_repos(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Get all repos this user has indexed.
    Used by the sidebar to show the user's repo list.
    """
    sessions = db.query(RepoSession).filter(
        RepoSession.user_id == current_user.id
    ).order_by(RepoSession.updated_at.desc()).all()

    return ReposResponse(repos=[
        RepoSummary(
            repo_url        = s.repo_url,
            status          = s.status,
            chunks_count    = s.chunks_count or 0,
            files_count     = s.files_count  or 0,
            vectors_count   = s.vectors_count or 0,
            ingested_at     = s.ingested_at.isoformat() if s.ingested_at else None,
            collection_name = s.collection_name,
            message_count   = len(s.chat_history or [])
        )
        for s in sessions
    ])


@router.get("/chat", response_model=ChatHistoryResponse)
def get_chat_history(
    repo_url:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Get chat history for a specific repo.
    Called when user switches to a previously indexed repo.
    """
    session = db.query(RepoSession).filter(
        RepoSession.user_id == current_user.id,
        RepoSession.repo_url == repo_url
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Repo session not found")

    return ChatHistoryResponse(
        repo_url     = repo_url,
        chat_history = session.chat_history or []
    )


@router.post("/chat/append")
def append_message(
    req:          AppendMessageRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Append a message to a repo's chat history.
    Called after every user question and assistant response.
    """
    session = db.query(RepoSession).filter(
        RepoSession.user_id  == current_user.id,
        RepoSession.repo_url == req.repo_url
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Repo session not found")

    # Append new message
    history = list(session.chat_history or [])
    history.append(req.message.dict())

    session.chat_history = history
    session.updated_at   = datetime.utcnow()
    db.commit()

    return {"message": "Appended", "total_messages": len(history)}


@router.post("/chat/clear")
def clear_chat(
    req:          ClearChatRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Clear chat history for a specific repo.
    Keeps the index intact — just clears the conversation.
    """
    session = db.query(RepoSession).filter(
        RepoSession.user_id  == current_user.id,
        RepoSession.repo_url == req.repo_url
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Repo session not found")

    session.chat_history = []
    session.updated_at   = datetime.utcnow()
    db.commit()

    return {"message": "Chat history cleared"}


@router.delete("/{repo_url:path}")
def delete_repo(
    repo_url:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Delete a repo session and its ChromaDB collection.
    Called when the user clicks Delete on a repo.
    """
    session = db.query(RepoSession).filter(
        RepoSession.user_id  == current_user.id,
        RepoSession.repo_url == repo_url
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Repo session not found")

    # Delete Qdrant collection for this user+repo
    try:
        import hashlib
        from qdrant_client import QdrantClient
        from backend.config import QDRANT_URL, QDRANT_API_KEY, QDRANT_LOCAL_PATH
        combined        = f"{str(current_user.id)}:{repo_url}"
        repo_hash       = hashlib.md5(combined.encode()).hexdigest()[:16]
        collection_name = f"repo_{repo_hash}"
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY) if QDRANT_URL                  else QdrantClient(path=QDRANT_LOCAL_PATH)
        client.delete_collection(collection_name)
        print(f"[DELETE] Qdrant collection deleted: {collection_name}")
    except Exception as e:
        print(f"[DELETE] Qdrant cleanup warning: {e}")

    db.delete(session)
    db.commit()

    return {"message": f"Repo deleted: {repo_url}"}