import pytest
from app.services.slot_manager import SlotManager
from app.services.rules_engine import DeterministicRulesEngine
from app.services.retriever import retriever
from app.database.connection import get_db
from seed_data import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database()

def test_billing_complaint():
    """PS04: Billing complaint slot extraction (amount and item)."""
    category, slots, missing = SlotManager.detect_category_and_slots(
        user_message="I want to dispute an unexpected roaming charge of $45 on my bill",
        current_slots={}
    )
    assert category == "billing_complaint"
    assert slots.get("disputed_amount") == 45.0
    assert slots.get("disputed_item") == "roaming"
    assert len(missing) == 0

def test_connection_problem():
    """PS04: Connection problem slot extraction (light status)."""
    category, slots, missing = SlotManager.detect_category_and_slots(
        user_message="My broadband connection is down and the optical light is blinking red on my ONT box",
        current_slots={}
    )
    assert category == "connection_problem"
    assert slots.get("ont_light_status") == "blinking red"
    assert len(missing) == 0

def test_mobile_issue():
    """PS04: Mobile issue slot extraction (device model)."""
    category, slots, missing = SlotManager.detect_category_and_slots(
        user_message="I am having mobile network and cellular service issues on my Galaxy S24",
        current_slots={}
    )
    assert category == "mobile_issue"
    assert "galaxy s24" in slots.get("device_model", "").lower()
    assert len(missing) == 0

def test_plan_question():
    """PS04: Plan question slot extraction (target plan)."""
    category, slots, missing = SlotManager.detect_category_and_slots(
        user_message="I want to ask about upgrading my plan to Gigabit Fiber",
        current_slots={}
    )
    assert category == "plan_question"
    assert "gigabit" in slots.get("target_plan", "").lower()
    assert len(missing) == 0

def test_missing_information():
    """PS04: Missing information detection and clarification prompt."""
    category, slots, missing = SlotManager.detect_category_and_slots(
        user_message="I need to file a billing dispute for an unexpected charge on my bill",
        current_slots={}
    )
    assert category == "billing_complaint"
    assert "disputed_item" in missing
    assert "disputed_amount" in missing
    prompt = SlotManager.get_prompt_for_missing_slot(category, missing[0])
    assert "disputing" in prompt or "item" in prompt or "charge" in prompt

def test_human_escalation():
    """PS04: Escalation trigger to human specialist."""
    result = DeterministicRulesEngine.evaluate_pre_checks(
        customer_id="CUST-1001",
        user_message="I want to speak directly to a human specialist right now",
        session_history=[]
    )
    assert result is not None
    assert result["action"] == "ESCALATE"
    assert result["reason"] == "EXPLICIT_HUMAN_REQUEST"
    assert "human specialist" in result["response"].lower()

def test_article_retrieval():
    """PS04: Knowledge base SOP article retrieval."""
    results = retriever.search(query="blinking red optical light on ont fiber box", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-CONN-01"
    assert "Fibre ONT Red Optical" in top["title"]
    assert top["score"] > 0.3

def test_customer_lookup():
    """PS04: Customer account context and telemetry lookup."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.customer_id, c.full_name, c.verification_status,
                   a.account_id, a.plan_name, a.balance_due,
                   t.modem_online, t.optical_rx_power_dbm
            FROM customers c
            JOIN accounts a ON c.customer_id = a.customer_id
            JOIN line_telemetry t ON a.account_id = t.account_id
            WHERE c.customer_id = 'CUST-1001'
            """
        )
        row = cursor.fetchone()

    assert row is not None
    assert row["customer_id"] == "CUST-1001"
    assert row["full_name"] == "John Doe"
    assert row["verification_status"] == "VERIFIED"
    assert row["account_id"] == "ACC-2001"
    assert "Fibre" in row["plan_name"]
    assert row["optical_rx_power_dbm"] is not None
