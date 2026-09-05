import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.database.connection import get_db

class EscalationManager:
    """
    Manages human agent escalation, creates structured handover tickets,
    and updates session statuses in SQLite.
    """

    @classmethod
    def create_escalation_ticket(
        cls,
        session_id: str,
        customer_id: str,
        category: str,
        reason: str,
        priority: str,
        custom_summary: Optional[str] = None,
        attempted_steps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Creates an escalation ticket in SQLite with structured handover summary."""
        ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"

        with get_db() as conn:
            cursor = conn.cursor()

            # Get customer details
            cursor.execute(
                """
                SELECT c.full_name, c.email, c.phone,
                       a.account_id, a.plan_name, a.balance_due,
                       t.optical_rx_power_dbm, t.optical_los_alarm
                FROM customers c
                LEFT JOIN accounts a ON c.customer_id = a.customer_id
                LEFT JOIN line_telemetry t ON a.account_id = t.account_id
                WHERE c.customer_id = ?
                """,
                (customer_id,)
            )
            cust = cursor.fetchone()

            # Extract recent messages to summarize attempted steps if not provided
            if not attempted_steps:
                cursor.execute(
                    """
                    SELECT sender, content FROM chat_messages
                    WHERE session_id = ? ORDER BY message_id ASC
                    """,
                    (session_id,)
                )
                msgs = cursor.fetchall()
                steps = []
                for m in msgs:
                    if m["sender"] == "ASSISTANT":
                        c_text = m["content"]
                        if "power cycle" in c_text.lower() or "reboot" in c_text.lower():
                            steps.append("Guided ONT/Router power cycle")
                        elif "cable" in c_text.lower() or "patch" in c_text.lower():
                            steps.append("Inspected green SC/APC optical patch cable")
                        elif "credit" in c_text.lower() or "refund" in c_text.lower():
                            steps.append("Checked auto-credit policy limit ($50.00)")
                attempted_steps = steps or ["Customer inquiry initiated"]

            # Construct structured handover summary if not already provided
            if not custom_summary:
                cust_name = cust["full_name"] if cust else "Unknown Customer"
                plan = cust["plan_name"] if cust else "Standard Plan"
                acc_id = cust["account_id"] if cust else "N/A"
                opt_power = cust["optical_rx_power_dbm"] if cust else "N/A"

                steps_str = "\n".join([f"  - {s}" for s in attempted_steps])
                custom_summary = (
                    f"### Human Handover Briefing [{ticket_id}]\n"
                    f"**Customer**: {cust_name} (Acct: {acc_id}) | Plan: {plan}\n"
                    f"**Category**: {category.upper()} | **Priority**: {priority}\n"
                    f"**Reason for Escalation**: {reason.replace('_', ' ').title()}\n\n"
                    f"**Troubleshooting Completed by AI**:\n{steps_str}\n\n"
                    f"**Telemetry / Ground Truth**:\n"
                    f"  - Optical Rx Power: {opt_power} dBm (Critical: -27.0 dBm)\n\n"
                    f"**Recommended Operator Action**:\n"
                    f"  - Immediate human agent engagement required; avoid repeating initial troubleshooting steps."
                )

            # Insert ticket
            conn.execute(
                """
                INSERT INTO escalation_tickets
                (ticket_id, session_id, customer_id, priority, category, reason, handover_summary, attempted_steps_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
                """,
                (
                    ticket_id,
                    session_id,
                    customer_id,
                    priority,
                    category,
                    reason,
                    custom_summary,
                    json.dumps(attempted_steps)
                )
            )

            # Update session status
            conn.execute(
                "UPDATE chat_sessions SET status = 'ESCALATED', updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,)
            )

        return {
            "ticket_id": ticket_id,
            "priority": priority,
            "category": category,
            "reason": reason,
            "handover_summary": custom_summary,
            "status": "OPEN"
        }

    @classmethod
    def get_open_tickets(cls) -> List[Dict[str, Any]]:
        """Returns all open and in-progress tickets for the Human Agent Ops view."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.ticket_id, t.session_id, t.customer_id, c.full_name as customer_name,
                       t.priority, t.category, t.reason, t.handover_summary,
                       t.attempted_steps_json, t.assigned_agent, t.status, t.created_at
                FROM escalation_tickets t
                JOIN customers c ON t.customer_id = c.customer_id
                ORDER BY CASE t.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    ELSE 4 END, t.created_at DESC
                """
            )
            rows = cursor.fetchall()

        tickets = []
        for r in rows:
            tickets.append({
                "ticket_id": r["ticket_id"],
                "session_id": r["session_id"],
                "customer_id": r["customer_id"],
                "customer_name": r["customer_name"],
                "priority": r["priority"],
                "category": r["category"],
                "reason": r["reason"],
                "handover_summary": r["handover_summary"],
                "attempted_steps": json.loads(r["attempted_steps_json"] or "[]"),
                "assigned_agent": r["assigned_agent"],
                "status": r["status"],
                "created_at": str(r["created_at"])
            })
        return tickets

    @classmethod
    def resolve_ticket(cls, ticket_id: str, agent_name: str = "Agent Alex") -> bool:
        """Marks a ticket as resolved by a human agent."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE escalation_tickets
                SET status = 'RESOLVED', assigned_agent = ?
                WHERE ticket_id = ?
                """,
                (agent_name, ticket_id)
            )
            return cursor.rowcount > 0
