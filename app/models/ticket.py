from typing import List, Optional
from pydantic import BaseModel

class EscalationTicketModel(BaseModel):
    ticket_id: str
    session_id: str
    customer_id: str
    customer_name: Optional[str] = None
    priority: str
    category: str
    reason: str
    handover_summary: str
    attempted_steps: List[str] = []
    assigned_agent: Optional[str] = None
    status: str
    created_at: str

class TicketResolveRequest(BaseModel):
    resolution_notes: str
    status: str = "RESOLVED"
