from fastapi import APIRouter, Query
from typing import List, Optional
from app.database.connection import get_db
from app.services.retriever import retriever

router = APIRouter(prefix="/api/kb", tags=["KnowledgeBase"])

@router.get("/articles")
async def list_articles(category: Optional[str] = None):
    """Retrieves list of local knowledge base support articles."""
    with get_db() as conn:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT article_id, category, title, summary, policy_code, last_updated FROM kb_articles WHERE category = ? ORDER BY article_id ASC",
                (category.lower(),)
            )
        else:
            cursor.execute(
                "SELECT article_id, category, title, summary, policy_code, last_updated FROM kb_articles ORDER BY category ASC, article_id ASC"
            )
        rows = cursor.fetchall()

    return [
        {
            "article_id": r["article_id"],
            "category": r["category"],
            "title": r["title"],
            "summary": r["summary"],
            "policy_code": r["policy_code"],
            "last_updated": str(r["last_updated"])
        }
        for r in rows
    ]

@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Fetches full content of an individual support article."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT article_id, category, title, summary, content, keywords, policy_code, last_updated FROM kb_articles WHERE article_id = ?",
            (article_id,)
        )
        r = cursor.fetchone()

    if not r:
        return {"error": "Article not found"}

    return {
        "article_id": r["article_id"],
        "category": r["category"],
        "title": r["title"],
        "summary": r["summary"],
        "content": r["content"],
        "keywords": r["keywords"],
        "policy_code": r["policy_code"],
        "last_updated": str(r["last_updated"])
    }

@router.get("/search")
async def search_kb(q: str = Query(..., min_length=1), category: Optional[str] = None):
    """Queries the local similarity retriever directly."""
    results = retriever.search(query=q, category=category, top_k=5)
    return {"query": q, "results": results}
