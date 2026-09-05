import uuid
import json
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.database.connection import get_db
from app.models.chat import ChatMessageRequest, ChatMessageResponse, CitationItem
from app.services.rules_engine import DeterministicRulesEngine
from app.services.retriever import retriever
from app.services.slot_manager import SlotManager
from app.services.gemini_service import gemini_service
from app.services.escalation_manager import EscalationManager

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(payload: ChatMessageRequest):
    customer_id = payload.customer_id
    user_msg = payload.message.strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Fetch customer details
        cursor.execute(
            """
            SELECT c.customer_id, c.full_name, c.email, c.phone, c.verification_status,
                   a.account_id, a.plan_name, a.balance_due, a.status as account_status, a.roaming_enabled,
                   t.modem_online, t.optical_rx_power_dbm, t.optical_los_alarm,
                   t.area_outage_detected, t.area_outage_eta
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            LEFT JOIN line_telemetry t ON a.account_id = t.account_id
            WHERE c.customer_id = ?
            """,
            (customer_id,)
        )
        cust_row = cursor.fetchone()
        if not cust_row:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

        # 2. Get or create session
        session_id = payload.session_id
        if not session_id:
            session_id = f"SESS-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO chat_sessions (session_id, customer_id, status) VALUES (?, ?, 'ACTIVE')",
                (session_id, customer_id)
            )
        else:
            cursor.execute("SELECT session_id, status FROM chat_sessions WHERE session_id = ?", (session_id,))
            s_row = cursor.fetchone()
            if not s_row:
                conn.execute(
                    "INSERT INTO chat_sessions (session_id, customer_id, status) VALUES (?, ?, 'ACTIVE')",
                    (session_id, customer_id)
                )

        # 3. Load conversation history
        cursor.execute(
            "SELECT sender, content, slots_json FROM chat_messages WHERE session_id = ? ORDER BY message_id ASC",
            (session_id,)
        )
        history_rows = cursor.fetchall()
        history = [{"sender": r["sender"], "content": r["content"]} for r in history_rows]

        # Extract current slots from previous messages
        current_slots = {}
        for r in history_rows:
            if r["slots_json"]:
                try:
                    current_slots.update(json.loads(r["slots_json"]))
                except Exception:
                    pass

        # Save incoming customer message
        conn.execute(
            "INSERT INTO chat_messages (session_id, sender, content) VALUES (?, 'CUSTOMER', ?)",
            (session_id, user_msg)
        )

    # Convert customer info to dict
    customer_info = {
        "customer_id": cust_row["customer_id"],
        "full_name": cust_row["full_name"],
        "email": cust_row["email"],
        "phone": cust_row["phone"],
        "verification_status": cust_row["verification_status"],
        "account": {
            "account_id": cust_row["account_id"],
            "plan_name": cust_row["plan_name"],
            "balance_due": cust_row["balance_due"],
            "account_status": cust_row["account_status"],
            "roaming_enabled": bool(cust_row["roaming_enabled"])
        }
    }
    telemetry_info = {
        "modem_online": bool(cust_row["modem_online"]),
        "optical_rx_power_dbm": cust_row["optical_rx_power_dbm"],
        "optical_los_alarm": bool(cust_row["optical_los_alarm"]),
        "area_outage_detected": bool(cust_row["area_outage_detected"]),
        "area_outage_eta": cust_row["area_outage_eta"]
    }

    # -----------------------------------------------------------------
    # STEP 4: Deterministic Pre-Check Rules Engine
    # -----------------------------------------------------------------
    pre_result = DeterministicRulesEngine.evaluate_pre_checks(
        customer_id=customer_id,
        user_message=user_msg,
        session_history=history
    )

    if pre_result:
        action = pre_result.get("action")
        response_text = pre_result["response"]
        citations = [CitationItem(**c) for c in pre_result.get("citations", [])]
        quick_replies = pre_result.get("suggested_quick_replies", [])

        if action == "ESCALATE":
            ticket = EscalationManager.create_escalation_ticket(
                session_id=session_id,
                customer_id=customer_id,
                category=pre_result.get("category", "support"),
                reason=pre_result["reason"],
                priority=pre_result.get("priority", "HIGH"),
                custom_summary=None
            )
            # Save assistant response
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO chat_messages (session_id, sender, content, citations_json) VALUES (?, 'ASSISTANT', ?, ?)",
                    (session_id, response_text, json.dumps([c.model_dump() for c in citations]))
                )

            return ChatMessageResponse(
                session_id=session_id,
                sender="ASSISTANT",
                content=response_text,
                status="ESCALATED",
                category="escalation",
                citations=citations,
                escalation_ticket_id=ticket["ticket_id"],
                is_grounded=True,
                suggested_quick_replies=quick_replies
            )

        elif action == "DETERMINISTIC_INTERCEPT":
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO chat_messages (session_id, sender, content, citations_json) VALUES (?, 'ASSISTANT', ?, ?)",
                    (session_id, response_text, json.dumps([c.model_dump() for c in citations]))
                )
            return ChatMessageResponse(
                session_id=session_id,
                sender="ASSISTANT",
                content=response_text,
                status="RESOLVED",
                category="connection",
                citations=citations,
                is_grounded=True,
                suggested_quick_replies=quick_replies
            )

    # -----------------------------------------------------------------
    # STEP 5: Category & Slot Filling Analysis
    # -----------------------------------------------------------------
    detected_cat, updated_slots, missing_slots = SlotManager.detect_category_and_slots(
        user_msg, current_slots
    )

    # Check for billing dispute amount limit
    if detected_cat in ["billing_refund", "billing_complaint"] and updated_slots.get("disputed_amount"):
        amount = float(updated_slots["disputed_amount"])
        rule_eval = DeterministicRulesEngine.evaluate_billing_rules(
            customer_id=customer_id,
            requested_amount=amount,
            reason_type=updated_slots.get("disputed_item", "disputed_charge")
        )

        citation_list = [CitationItem(**rule_eval["citation"])] if rule_eval.get("citation") else []

        if rule_eval["allowed"]:
            # Auto-approved courtesy credit!
            resp_text = rule_eval["message"]
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO chat_messages (session_id, sender, content, citations_json, slots_json) VALUES (?, 'ASSISTANT', ?, ?, ?)",
                    (session_id, resp_text, json.dumps([c.model_dump() for c in citation_list]), json.dumps(updated_slots))
                )
            return ChatMessageResponse(
                session_id=session_id,
                sender="ASSISTANT",
                content=resp_text,
                status="RESOLVED",
                category="billing",
                citations=citation_list,
                is_grounded=True,
                suggested_quick_replies=["Download Updated Invoice", "Return to Menu"]
            )
        else:
            # Exceeds limit -> Escalate to human
            resp_text = (
                f"{rule_eval['message']}\n\n"
                f"I have created an escalation ticket for our Billing Operations Management team. "
                f"They will review your invoice line item and get in touch with you within 1 business day."
            )
            ticket = EscalationManager.create_escalation_ticket(
                session_id=session_id,
                customer_id=customer_id,
                category="billing",
                reason="REFUND_LIMIT_EXCEEDED",
                priority="MEDIUM",
                custom_summary=(
                    f"### Billing Dispute Handover [{customer_id}]\n"
                    f"**Customer**: {customer_info['full_name']} | Acct: {customer_info['account']['account_id']}\n"
                    f"**Disputed Amount**: ${amount:.2f} (Requested courtesy credit exceeds automated limit of $50.00)\n"
                    f"**Disputed Item**: {updated_slots.get('disputed_item', 'Unspecified charge')}\n"
                    f"**Account Balance**: ${customer_info['account']['balance_due']:.2f}\n"
                    f"**Recommended Action**: Review billing ledger and approve/deny supervisor override."
                )
            )
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO chat_messages (session_id, sender, content, citations_json, slots_json) VALUES (?, 'ASSISTANT', ?, ?, ?)",
                    (session_id, resp_text, json.dumps([c.model_dump() for c in citation_list]), json.dumps(updated_slots))
                )
            return ChatMessageResponse(
                session_id=session_id,
                sender="ASSISTANT",
                content=resp_text,
                status="ESCALATED",
                category="billing",
                citations=citation_list,
                escalation_ticket_id=ticket["ticket_id"],
                is_grounded=True,
                suggested_quick_replies=["Track Ticket Status", "Contact Supervisor Directly"]
            )

    # If missing required slots and user didn't ask a general question, ask for missing info
    if missing_slots and not ("what" in user_msg.lower() or "how" in user_msg.lower() or "policy" in user_msg.lower()):
        next_slot = missing_slots[0]
        prompt_text = SlotManager.get_prompt_for_missing_slot(detected_cat, next_slot)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, sender, content, slots_json) VALUES (?, 'ASSISTANT', ?, ?)",
                (session_id, prompt_text, json.dumps(updated_slots))
            )

        quick_replies = []
        if next_slot == "ont_light_status":
            quick_replies = ["Solid Red", "Blinking Red", "Solid Green", "Lights are Off"]
        elif next_slot == "disputed_item":
            quick_replies = ["Roaming Surcharge", "Data Overage", "Late Fee Charge"]
        elif next_slot == "device_model":
            quick_replies = ["iPhone 15", "Samsung Galaxy S24", "Google Pixel 8"]
        elif next_slot == "target_plan":
            quick_replies = ["Gigabit Pro 1Gbps", "UltraFibre 500Mbps", "5G Unlimited Max"]

        return ChatMessageResponse(
            session_id=session_id,
            sender="ASSISTANT",
            content=prompt_text,
            status="NEEDS_INFO",
            category=detected_cat,
            missing_slots=missing_slots,
            is_grounded=True,
            suggested_quick_replies=quick_replies
        )

    # -----------------------------------------------------------------
    # STEP 6: Local Knowledge Base Retrieval
    # -----------------------------------------------------------------
    kb_category = "billing" if "billing" in (detected_cat or "") else ("connection" if "connection" in (detected_cat or "") else ("mobile" if "mobile" in (detected_cat or "") else ("plans" if "plan" in (detected_cat or "") else None)))
    kb_results = retriever.search(query=user_msg, category=kb_category, top_k=3)

    # -----------------------------------------------------------------
    # STEP 7: Grounded AI Reasoning (Gemini or Fallback)
    # -----------------------------------------------------------------
    ai_result = gemini_service.generate_grounded_response(
        customer_info=customer_info,
        telemetry_info=telemetry_info,
        kb_chunks=kb_results,
        conversation_history=history,
        user_message=user_msg
    )

    resp_content = ai_result["content"]
    citations = [CitationItem(**c) for c in ai_result["citations"]]

    # Save to database
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, sender, content, citations_json, slots_json) VALUES (?, 'ASSISTANT', ?, ?, ?)",
            (session_id, resp_content, json.dumps([c.model_dump() for c in citations]), json.dumps(updated_slots))
        )

    # Provide contextual quick replies
    quick_replies = []
    if "KB-CONN-01" in resp_content:
        quick_replies = ["I power-cycled the ONT", "Yellow cable is secure", "Light is still red"]
    elif "KB-MOB-01" in resp_content:
        quick_replies = ["My QR code expired", "Need step-by-step for iPhone", "Setup complete!"]
    elif "KB-PLAN-01" in resp_content:
        quick_replies = ["Confirm Gigabit Upgrade", "Compare all plans", "Keep current plan"]

    return ChatMessageResponse(
        session_id=session_id,
        sender="ASSISTANT",
        content=resp_content,
        status="ACTIVE",
        category=ai_result.get("category", "general"),
        citations=citations,
        is_grounded=ai_result.get("is_grounded", True),
        suggested_quick_replies=quick_replies
    )

@router.get("/history/{session_id}")
async def get_session_history(session_id: str):
    """Retrieves conversation history and citations for a session."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT message_id, sender, content, citations_json, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY message_id ASC
            """,
            (session_id,)
        )
        rows = cursor.fetchall()

    messages = []
    for r in rows:
        citations = []
        if r["citations_json"]:
            try:
                citations = json.loads(r["citations_json"])
            except Exception:
                pass
        messages.append({
            "message_id": r["message_id"],
            "sender": r["sender"],
            "content": r["content"],
            "citations": citations,
            "created_at": str(r["created_at"])
        })

    return {"session_id": session_id, "messages": messages}

@router.post("/reset")
async def reset_session(customer_id: str):
    """Generates a fresh session ID for a chosen customer."""
    new_session_id = f"SESS-{uuid.uuid4().hex[:8]}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id, customer_id, status) VALUES (?, ?, 'ACTIVE')",
            (new_session_id, customer_id)
        )
    return {"session_id": new_session_id, "customer_id": customer_id}
