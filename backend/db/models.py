import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.db.connection import Base


class User(Base):
    """
    Stores registered users.
    Password is always stored as bcrypt hash — never plaintext.
    Email must be verified before the user can log in.
    """
    __tablename__ = "users"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email              = Column(String(255), unique=True, nullable=False, index=True)
    password_hash      = Column(String(255), nullable=False)
    is_verified        = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(64), nullable=True, index=True)
    token_expires_at   = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    # Relationships
    api_keys      = relationship("ApiKey",      back_populates="user", cascade="all, delete-orphan")
    repo_sessions = relationship("RepoSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class ApiKey(Base):
    """
    Stores encrypted API keys per user per provider.
    Keys are AES-256 encrypted using APP_SECRET before storage.
    Plaintext keys are NEVER stored.

    provider examples: google, openai, groq, openrouter, anthropic
    key_type examples: embedding, llm
    """
    __tablename__ = "api_keys"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider      = Column(String(50),  nullable=False)
    key_type      = Column(String(50),  nullable=False)
    encrypted_key = Column(Text,        nullable=False)
    model_name    = Column(String(100), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "key_type", name="uq_user_provider_keytype"),
    )

    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey {self.provider}/{self.key_type} for user {self.user_id}>"


class RepoSession(Base):
    """
    Stores each user's indexed repositories and their chat history.
    """
    __tablename__ = "repo_sessions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    repo_url        = Column(String(500), nullable=False)
    status          = Column(String(50),  default="pending")
    chunks_count    = Column(Integer,     default=0)
    files_count     = Column(Integer,     default=0)
    vectors_count   = Column(Integer,     default=0)
    ingested_at     = Column(DateTime,    nullable=True)
    collection_name = Column(String(100), nullable=True)
    chat_history    = Column(JSON,        default=list)
    error_message   = Column(Text,        nullable=True)
    created_at      = Column(DateTime,    default=datetime.utcnow)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "repo_url", name="uq_user_repo"),
    )

    user = relationship("User", back_populates="repo_sessions")

    def __repr__(self):
        return f"<RepoSession {self.repo_url} for user {self.user_id}>"