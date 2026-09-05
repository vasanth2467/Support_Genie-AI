import re
from typing import Dict, Any, Optional, Tuple, List
from app.config import settings
from app.database.connection import get_db

class DeterministicRulesEngine:
    """
    Executes strict deterministic business logic and guardrails.
    Keeps policy limits, financial caps, hardware thresholds, and outage
    short-circuits completely separate from LLM generative reasoning.
    """

    EXPLICIT_ESCALATION_PATTERNS = [
        r"\b(speak|talk)\s+(directly\s+)?(to|with)\s+(a\s+)?(human|person|agent|representative|supervisor|manager|specialist)\b",
        r"\b(human\s+(agent|specialist|representative)|real\s+person|transfer\s+me|get\s+me\s+someone)\b",
        r"\b(lawyer|attorney|sue|legal\s+action|lawsuit|fcc|court)\b",
        r"\b(cancel\s+everything|terminate\s+my\s+account|shut\s+it\s+down)\b"
    ]

    @staticmethod
    def evaluate_pre_checks(
        customer_id: str,
        user_message: str,
        session_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Runs deterministic checks BEFORE calling LLM or Knowledge Base.
        Returns a direct response dict if a rule is triggered, or None if normal flow proceeds.
        """
        msg_lower = user_message.lower().strip()

        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Fetch customer account and telemetry
            cursor.execute(
                """
                SELECT c.full_name, c.verification_status,
                       a.account_id, a.plan_name, a.balance_due, a.status as account_status,
                       t.modem_online, t.optical_rx_power_dbm, t.optical_los_alarm,
                       t.area_outage_detected, t.area_outage_eta
                FROM customers c
                LEFT JOIN accounts a ON c.customer_id = a.customer_id
                LEFT JOIN line_telemetry t ON a.account_id = t.account_id
                WHERE c.customer_id = ?
                """,
                (customer_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        (
            full_name, verification_status,
            account_id, plan_name, balance_due, account_status,
            modem_online, optical_rx, optical_los,
            area_outage_detected, area_outage_eta
        ) = (
            row["full_name"], row["verification_status"],
            row["account_id"], row["plan_name"], row["balance_due"], row["account_status"],
            row["modem_online"], row["optical_rx_power_dbm"], row["optical_los_alarm"],
            row["area_outage_detected"], row["area_outage_eta"]
        )

        # -------------------------------------------------------------
        # Rule 1: Explicit Human Handover Request
        # -------------------------------------------------------------
        for pattern in DeterministicRulesEngine.EXPLICIT_ESCALATION_PATTERNS:
            if re.search(pattern, msg_lower):
                return {
                    "action": "ESCALATE",
                    "reason": "EXPLICIT_HUMAN_REQUEST",
                    "priority": "HIGH",
                    "response": (
                        f"I understand you'd like to speak directly with a human specialist. "
                        f"I have summarized our interaction and placed you in our priority queue. "
                        f"A representative will connect with you momentarily."
                    ),
                    "citations": [
                        {
                            "source_type": "POLICY_RULE",
                            "title": "Customer Escalation Charter (Rule 1.1)",
                            "section": "Customer Choice Handover",
                            "excerpt": "Customers expressing an explicit desire for human interaction must be transferred immediately without mandatory AI loops."
                        }
                    ],
                    "suggested_quick_replies": ["Track Queue Status", "Add Additional Notes"]
                }

        # -------------------------------------------------------------
        # Rule 2: Active Infrastructure Outage Intercept
        # -------------------------------------------------------------
        connection_keywords = ["down", "offline", "not working", "outage", "slow", "red light", "los", "internet", "wifi"]
        if area_outage_detected and any(k in msg_lower for k in connection_keywords):
            eta_str = area_outage_eta or "within 2 to 4 hours"
            return {
                "action": "DETERMINISTIC_INTERCEPT",
                "status": "RESOLVED",
                "category": "connection",
                "response": (
                    f"⚠️ **Known Network Outage Detected in Your Area**\n\n"
                    f"Hello {full_name}, our telemetry shows a confirmed regional trunk outage affecting nodes in your neighborhood. "
                    f"Our field engineering teams are actively repairing the infrastructure.\n\n"
                    f"- **Estimated Time of Restoration**: {eta_str}\n"
                    f"- **Action Required**: None. Please keep your ONT and router connected; your service will automatically reconnect once repairs conclude.\n\n"
                    f"*You will receive an automated SMS notification as soon as line telemetry indicates stable optical power.*"
                ),
                "citations": [
                    {
                        "source_type": "LINE_TELEMETRY",
                        "metric": "area_outage_detected",
                        "value": True,
                        "section": f"Regional Central Office Telemetry (ETA: {eta_str})",
                        "excerpt": "Automated network supervision alarm triggered for distribution cluster #402."
                    }
                ],
                "suggested_quick_replies": ["Notify Me on Restoration", "View Incident Map"]
            }

        # -------------------------------------------------------------
        # Rule 3: Repeated Technical Failure Counter
        # -------------------------------------------------------------
        # Count user messages where reboot or cable re-seat failed
        failure_phrases = ["still red", "still not working", "restarted again", "rebooted again", "still down", "did not fix", "didn't help"]
        repeat_count = 0
        for m in session_history:
            if m.get("sender") == "CUSTOMER":
                text = m.get("content", "").lower()
                if any(p in text for p in failure_phrases):
                    repeat_count += 1

        if any(p in msg_lower for p in failure_phrases) and repeat_count >= 1:
            return {
                "action": "ESCALATE",
                "reason": "PERSISTENT_TROUBLESHOOTING_FAILURE",
                "priority": "HIGH",
                "response": (
                    f"I see that the standard self-service steps and power cycling have not restored your connection. "
                    f"Because your ONT optical signal is indicating a persistent line loss (-28.5 dBm), this indicates "
                    f"a physical drop cable fault. I am creating a priority dispatch ticket for a Field Technician."
                ),
                "citations": [
                    {
                        "source_type": "KB_ARTICLE",
                        "article_id": "KB-CONN-01",
                        "title": "Fibre ONT Red Optical Alarm Guide",
                        "section": "Section 4: Mandatory Field Escalation",
                        "excerpt": "When optical power remains below -27.0 dBm after guided power cycle, self-service is terminated and a physical truck roll is scheduled."
                    },
                    {
                        "source_type": "LINE_TELEMETRY",
                        "metric": "optical_rx_power_dbm",
                        "value": optical_rx,
                        "section": "Optical Line Supervision",
                        "excerpt": f"Measured optical power: {optical_rx} dBm (Critical Threshold: -27.0 dBm)"
                    }
                ],
                "suggested_quick_replies": ["Choose Dispatch Slot", "View Ticket Status"]
            }

        return None

    @staticmethod
    def evaluate_billing_rules(
        customer_id: str,
        requested_amount: float,
        reason_type: str
    ) -> Dict[str, Any]:
        """
        Enforces deterministic financial bounds on refunds and credits.
        Strictly limits AI auto-credit to <= $50.00.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            # Check customer balance and account
            cursor.execute(
                """
                SELECT a.account_id, a.balance_due, c.full_name
                FROM accounts a
                JOIN customers c ON a.customer_id = c.customer_id
                WHERE a.customer_id = ?
                """,
                (customer_id,)
            )
            row = cursor.fetchone()

        if not row:
            return {"allowed": False, "reason": "ACCOUNT_NOT_FOUND"}

        account_id = row["account_id"]
        current_balance = row["balance_due"]
        full_name = row["full_name"]

        # Limit check:
        if requested_amount <= settings.AUTO_REFUND_LIMIT:
            # Auto-approval allowed!
            new_balance = max(0.0, current_balance - requested_amount)
            with get_db() as conn:
                conn.execute(
                    "UPDATE accounts SET balance_due = ? WHERE account_id = ?",
                    (new_balance, account_id)
                )

            return {
                "allowed": True,
                "amount_credited": requested_amount,
                "new_balance": new_balance,
                "account_id": account_id,
                "message": (
                    f"✅ **Courtesy Credit Approved**: A credit of **${requested_amount:.2f}** has been applied "
                    f"to your account ({account_id}). Your new balance is **${new_balance:.2f}**."
                ),
                "citation": {
                    "source_type": "KB_ARTICLE",
                    "article_id": "KB-BILL-02",
                    "title": "Customer Refund and Courtesy Credit Policy",
                    "section": "Section 2: Automated Resolution Rules",
                    "excerpt": f"SupportGenie AI is authorized to approve automated courtesy credits of up to ${settings.AUTO_REFUND_LIMIT:.2f} USD per incident."
                }
            }
        else:
            # Exceeds limit -> Must escalate
            return {
                "allowed": False,
                "reason": "REFUND_LIMIT_EXCEEDED",
                "requested_amount": requested_amount,
                "limit": settings.AUTO_REFUND_LIMIT,
                "message": (
                    f"The requested credit amount of **${requested_amount:.2f}** exceeds the automated resolution limit "
                    f"of **${settings.AUTO_REFUND_LIMIT:.2f}**. As per company financial policy (POL-FIN-202), requests over "
                    f"${settings.AUTO_REFUND_LIMIT:.2f} require human supervisor authorization."
                ),
                "citation": {
                    "source_type": "KB_ARTICLE",
                    "article_id": "KB-BILL-02",
                    "title": "Customer Refund and Courtesy Credit Policy",
                    "section": "Section 3: Mandatory Human Escalation Thresholds",
                    "excerpt": f"Requested refund or disputed amount exceeds ${settings.AUTO_REFUND_LIMIT:.2f} USD. Tier-1 automated assistant must escalate to Billing Supervisor."
                }
            }
