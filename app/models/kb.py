from typing import List, Optional
from pydantic import BaseModel

class KnowledgeArticleModel(BaseModel):
    article_id: str
    category: str
    title: str
    summary: str
    content: str
    keywords: Optional[str] = None
    policy_code: Optional[str] = None
    last_updated: Optional[str] = None

class KnowledgeSearchResult(BaseModel):
    article_id: str
    category: str
    title: str
    policy_code: Optional[str] = None
    score: float
    snippet: str
    matched_section: Optional[str] = None
