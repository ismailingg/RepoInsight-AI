# test_db.py (run once, then delete)
from backend.db.connection import init_db, engine
from sqlalchemy import text

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print("✓ Connected to PostgreSQL:", result.fetchone()[0])

# Create tables
init_db()
print("✓ All tables created successfully")