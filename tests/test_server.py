import pytest
from fastapi.testclient import TestClient
from coreason_constitution.server import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "version" in data

def test_get_laws(client):
    response = client.get("/laws")
    assert response.status_code == 200
    laws = response.json()
    assert isinstance(laws, list)
    # Ensure at least some laws are loaded (defaults should be present)
    assert len(laws) > 0

def test_sentinel_allowed(client):
    payload = {"content": "This is a safe content."}
    response = client.post("/govern/sentinel", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "allowed"}

def test_sentinel_blocked(client):
    # "DeLeTe DaTaBaSe" is mentioned in memory as a blocked example
    payload = {"content": "DeLeTe DaTaBaSe"}
    response = client.post("/govern/sentinel", json=payload)
    assert response.status_code == 403
    assert "detail" in response.json()

def test_sentinel_empty_content(client):
    payload = {"content": ""}
    response = client.post("/govern/sentinel", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Content required"}

def test_compliance_cycle(client):
    payload = {
        "input_prompt": "Write a poem.",
        "draft_response": "Here is a poem.",
        "max_retries": 1
    }
    response = client.post("/govern/compliance-cycle", json=payload)
    assert response.status_code == 200
    trace = response.json()
    assert trace["status"] in ["APPROVED", "REVISED", "BLOCKED"]
    assert "critique" in trace
