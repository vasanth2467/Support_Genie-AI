from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.escalation_manager import EscalationManager
from app.models.ticket import TicketResolveRequest

router = APIRouter(prefix="/api/tickets", tags=["Escalations"])

@router.get("")
async def list_tickets():
    """Fetches all escalated tickets for the Human Agent Ops queue."""
    return EscalationManager.get_open_tickets()

@router.post("/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, payload: TicketResolveRequest):
    """Resolves an escalated ticket with agent notes."""
    success = EscalationManager.resolve_ticket(ticket_id=ticket_id, agent_name="Human Agent Specialist")
    if not success:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found.")
    return {"status": "SUCCESS", "ticket_id": ticket_id, "resolution": payload.resolution_notes}
