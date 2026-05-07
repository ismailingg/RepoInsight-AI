import pytest
import os

# Set a dummy APP_SECRET for tests before importing anything that uses it
os.environ["APP_SECRET"] = "uL1M_xGj5k_T5T9V8M8P2N3J4K5L6M7N8O9P0Q1R2S3="

@pytest.fixture
def mock_db_session(mocker):
    return mocker.Mock()

@pytest.fixture
def mock_user():
    import uuid
    from backend.db.models import User
    return User(id=uuid.uuid4(), email="test@example.com")
