import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # max 5 persistent connections
    max_overflow=10,      # allow 10 extra connections under load
    pool_pre_ping=True,   # test connection before using (handles dropped connections)
    echo=False            # set True to log all SQL queries (useful for debugging)
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request.
    Automatically closes session when request is done.
    
    Usage in endpoints:
        @router.post("/something")
        def my_endpoint(db: Session = Depends(get_db)):
            ...
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
    # Import models so SQLAlchemy knows about them
    from backend.db import models   # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")