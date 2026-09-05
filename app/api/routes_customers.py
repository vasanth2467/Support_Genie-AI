from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.database.connection import get_db

router = APIRouter(prefix="/api/customers", tags=["Customers"])

class TelemetryUpdateRequest(BaseModel):
    modem_online: Optional[bool] = None
    optical_rx_power_dbm: Optional[float] = None
    optical_los_alarm: Optional[bool] = None
    area_outage_detected: Optional[bool] = None
    area_outage_eta: Optional[str] = None

@router.get("")
async def list_customers():
    """Lists all customers and their active subscription and telemetry overview."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.customer_id, c.full_name, c.email, c.phone, c.address, c.verification_status,
                   a.account_id, a.plan_name, a.category, a.balance_due, a.status as account_status,
                   t.modem_online, t.optical_rx_power_dbm, t.optical_los_alarm,
                   t.area_outage_detected, t.area_outage_eta
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            LEFT JOIN line_telemetry t ON a.account_id = t.account_id
            ORDER BY c.customer_id ASC
            """
        )
        rows = cursor.fetchall()

    results = []
    for r in rows:
        results.append({
            "customer_id": r["customer_id"],
            "full_name": r["full_name"],
            "email": r["email"],
            "phone": r["phone"],
            "address": r["address"],
            "verification_status": r["verification_status"],
            "plan_name": r["plan_name"],
            "category": r["category"],
            "balance_due": r["balance_due"],
            "account_status": r["account_status"],
            "telemetry": {
                "modem_online": bool(r["modem_online"]),
                "optical_rx_power_dbm": r["optical_rx_power_dbm"],
                "optical_los_alarm": bool(r["optical_los_alarm"]),
                "area_outage_detected": bool(r["area_outage_detected"]),
                "area_outage_eta": r["area_outage_eta"]
            }
        })
    return results

@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    """Fetches comprehensive account details, subscription, and line telemetry for a customer."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.customer_id, c.full_name, c.email, c.phone, c.address, c.verification_status,
                   a.account_id, a.plan_name, a.category, a.monthly_rate, a.balance_due, a.billing_cycle_day,
                   a.status as account_status, a.data_limit_gb, a.data_used_gb, a.roaming_enabled,
                   t.modem_online, t.optical_rx_power_dbm, t.optical_los_alarm, t.router_ip,
                   t.area_outage_detected, t.area_outage_eta, t.last_reboot_timestamp
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            LEFT JOIN line_telemetry t ON a.account_id = t.account_id
            WHERE c.customer_id = ?
            """,
            (customer_id,)
        )
        r = cursor.fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Customer not found.")

    return {
        "customer_id": r["customer_id"],
        "full_name": r["full_name"],
        "email": r["email"],
        "phone": r["phone"],
        "address": r["address"],
        "verification_status": r["verification_status"],
        "account": {
            "account_id": r["account_id"],
            "plan_name": r["plan_name"],
            "category": r["category"],
            "monthly_rate": r["monthly_rate"],
            "balance_due": r["balance_due"],
            "billing_cycle_day": r["billing_cycle_day"],
            "status": r["account_status"],
            "data_limit_gb": r["data_limit_gb"],
            "data_used_gb": r["data_used_gb"],
            "roaming_enabled": bool(r["roaming_enabled"])
        },
        "telemetry": {
            "modem_online": bool(r["modem_online"]),
            "optical_rx_power_dbm": r["optical_rx_power_dbm"],
            "optical_los_alarm": bool(r["optical_los_alarm"]),
            "router_ip": r["router_ip"],
            "area_outage_detected": bool(r["area_outage_detected"]),
            "area_outage_eta": r["area_outage_eta"],
            "last_reboot_timestamp": str(r["last_reboot_timestamp"]) if r["last_reboot_timestamp"] else None
        }
    }

@router.post("/{customer_id}/telemetry")
async def update_telemetry(customer_id: str, payload: TelemetryUpdateRequest):
    """Allows demo judges or users to simulate telemetry changes in real-time."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id FROM accounts WHERE customer_id = ?", (customer_id,))
        acc = cursor.fetchone()
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found.")

        acc_id = acc["account_id"]
        updates = []
        params = []

        if payload.modem_online is not None:
            updates.append("modem_online = ?")
            params.append(1 if payload.modem_online else 0)
        if payload.optical_rx_power_dbm is not None:
            updates.append("optical_rx_power_dbm = ?")
            params.append(payload.optical_rx_power_dbm)
        if payload.optical_los_alarm is not None:
            updates.append("optical_los_alarm = ?")
            params.append(1 if payload.optical_los_alarm else 0)
        if payload.area_outage_detected is not None:
            updates.append("area_outage_detected = ?")
            params.append(1 if payload.area_outage_detected else 0)
        if payload.area_outage_eta is not None:
            updates.append("area_outage_eta = ?")
            params.append(payload.area_outage_eta)

        if updates:
            sql = f"UPDATE line_telemetry SET {', '.join(updates)} WHERE account_id = ?"
            params.append(acc_id)
            conn.execute(sql, tuple(params))

    return {"status": "SUCCESS", "customer_id": customer_id, "account_id": acc_id}
