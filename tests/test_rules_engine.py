import pytest
from app.services.rules_engine import DeterministicRulesEngine
from app.database.connection import init_db
from seed_data import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database()

def test_explicit_human_escalation():
    result = DeterministicRulesEngine.evaluate_pre_checks(
        customer_id="CUST-1001",
        user_message="I want to speak to a human representative immediately",
        session_history=[]
    )
    assert result is not None
    assert result["action"] == "ESCALATE"
    assert result["reason"] == "EXPLICIT_HUMAN_REQUEST"
    assert "human specialist" in result["response"].lower()

def test_area_outage_deterministic_intercept():
    # CUST-1006 has area_outage_detected = True
    result = DeterministicRulesEngine.evaluate_pre_checks(
        customer_id="CUST-1006",
        user_message="My internet is completely down and not working",
        session_history=[]
    )
    assert result is not None
    assert result["action"] == "DETERMINISTIC_INTERCEPT"
    assert result["status"] == "RESOLVED"
    assert "Known Network Outage Detected" in result["response"]
    assert any(c["source_type"] == "LINE_TELEMETRY" for c in result["citations"])

def test_billing_refund_below_threshold():
    # $35 is <= $50 auto-credit limit
    eval_result = DeterministicRulesEngine.evaluate_billing_rules(
        customer_id="CUST-1003",
        requested_amount=35.00,
        reason_type="accidental data overage"
    )
    assert eval_result["allowed"] is True
    assert eval_result["amount_credited"] == 35.00
    assert "Courtesy Credit Approved" in eval_result["message"]

def test_billing_refund_above_threshold():
    # $140 exceeds $50 auto-credit limit -> Must escalate
    eval_result = DeterministicRulesEngine.evaluate_billing_rules(
        customer_id="CUST-1004",
        requested_amount=140.00,
        reason_type="roaming overcharge"
    )
    assert eval_result["allowed"] is False
    assert eval_result["reason"] == "REFUND_LIMIT_EXCEEDED"
    assert "exceeds the automated resolution limit" in eval_result["message"]
