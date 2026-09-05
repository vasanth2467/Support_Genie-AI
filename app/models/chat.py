from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class CitationItem(BaseModel):
    source_type: str            # 'KB_ARTICLE', 'LINE_TELEMETRY', 'POLICY_RULE'
    article_id: Optional[str] = None
    title: Optional[str] = None
    section: Optional[str] = None
    similarity_score: Optional[float] = None
    excerpt: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[Any] = None

class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = None
    customer_id: str
    message: str

class ChatMessageResponse(BaseModel):
    session_id: str
    sender: str
    content: str
    status: str                 # 'ACTIVE', 'RESOLVED', 'ESCALATED', 'NEEDS_INFO'
    category: Optional[str] = None
    citations: List[CitationItem] = []
    missing_slots: List[str] = []
    escalation_ticket_id: Optional[str] = None
    is_grounded: bool = True
    suggested_quick_replies: List[str] = []

class ChatHistoryItem(BaseModel):
    message_id: int
    sender: str
    content: str
    citations: List[CitationItem] = []
    created_at: str
