from fastapi.testclient import TestClient
from backend.Main import app
from backend.utils.auth import get_current_user
from backend.db.connection import get_db

client = TestClient(app)

def test_query_repo_no_keys(mocker, mock_user):
    # Mock authentication
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    # Mock database session
    mock_db = mocker.Mock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Mock get_user_keys to return no keys
    mocker.patch("backend.api.query.get_user_keys", return_value={})
    
    response = client.post(
        "/query", 
        json={"github_url": "https://github.com/test/repo", "question": "test?"}
    )
    
    assert response.status_code == 400
    assert "No embedding API key found" in response.json()["detail"]
    
    # Clean up
    app.dependency_overrides.clear()

def test_query_repo_not_ingested(mocker, mock_user):
    # Mock authentication
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    mock_db = mocker.Mock()
    # Mock the query to return None (repo not found/ingested)
    mock_db.query().filter().first.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db
    
    mocker.patch("backend.api.query.get_user_keys", return_value={
        "embedding_key": "enc_key", 
        "llm_key": "enc_key"
    })
    
    response = client.post(
        "/query", 
        json={"github_url": "https://github.com/test/repo", "question": "test?"}
    )
    
    assert response.status_code == 404
    assert "Repo not ingested yet" in response.json()["detail"]
    
    app.dependency_overrides.clear()
