import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# Neon (and some other hosted providers) give postgres:// — SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# connect_args for SSL — required by Neon, ignored by local postgres
connect_args = {}
if "neon.tech" in DATABASE_URL or "sslmode=require" in DATABASE_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(
    DATABASE_URL,
    connect_args  = connect_args,
    pool_size     = 5,
    max_overflow  = 10,
    pool_pre_ping = True,   # handles Neon's serverless cold starts
    pool_recycle  = 300,    # recycle connections every 5 min (Neon closes idle ones)
    echo          = False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request.
    Automatically closes session when request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables defined in models.py.
    Called once on app startup.
    """
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables ready")