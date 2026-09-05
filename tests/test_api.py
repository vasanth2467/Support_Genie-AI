import pytest
from fastapi.testclient import TestClient
from app.main import app
from seed_data import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database()

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["app"] == "SupportGenie AI"

def test_list_customers(client):
    response = client.get("/api/customers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6
    assert any(c["customer_id"] == "CUST-1001" for c in data)

def test_chat_flow_ont_red_light(client):
    payload = {
        "customer_id": "CUST-1001",
        "message": "My fiber box has a blinking red light and internet is down"
    }
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None
    assert "KB-CONN-01" in [c["article_id"] for c in data["citations"] if c.get("article_id")]
    assert "patch cable" in data["content"].lower() or "power" in data["content"].lower()

def test_chat_flow_billing_auto_approval(client):
    payload = {
        "customer_id": "CUST-1003",
        "message": "Can I get a refund of $35 for this accidental data overage charge on my bill?"
    }
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RESOLVED"
    assert "Credit Approved" in data["content"]
    assert any(c["article_id"] == "KB-BILL-02" for c in data["citations"] if c.get("article_id"))

def test_chat_flow_billing_escalation(client):
    payload = {
        "customer_id": "CUST-1004",
        "message": "I demand a refund of $140 for these outrageous roaming charges on my bill"
    }
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ESCALATED"
    assert data["escalation_ticket_id"] is not None
    assert "exceeds" in data["content"].lower()

    # Verify ticket in agent queue
    t_resp = client.get("/api/tickets")
    assert t_resp.status_code == 200
    tickets = t_resp.json()
    assert any(t["ticket_id"] == data["escalation_ticket_id"] for t in tickets)
