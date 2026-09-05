import re
import math
from typing import List, Dict, Any, Optional
from app.config import settings
from app.database.connection import get_db

class LocalKnowledgeRetriever:
    """
    Self-contained local similarity retrieval engine.
    Uses TF-IDF + BM25 keyword matching with cosine similarity over KB articles.
    Completely offline and local; requires no external cloud vector database.
    """

    def __init__(self):
        self._articles_cache: List[Dict[str, Any]] = []
        self._idf_cache: Dict[str, float] = {}
        self._avg_doc_len: float = 0.0
        self._load_and_index()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer that extracts lowercase alphanumeric words."""
        return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())

    def _load_and_index(self):
        """Loads articles from SQLite and builds the in-memory inverted index."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT article_id, category, title, summary, content, keywords, policy_code
                FROM kb_articles
                """
            )
            rows = cursor.fetchall()

        self._articles_cache = []
        doc_lengths = []
        df_counts: Dict[str, int] = {}

        for row in rows:
            art = {
                "article_id": row["article_id"],
                "category": row["category"],
                "title": row["title"],
                "summary": row["summary"],
                "content": row["content"],
                "keywords": row["keywords"] or "",
                "policy_code": row["policy_code"] or ""
            }

            # Index text = Title * 3 + Keywords * 3 + Summary * 2 + Content
            weighted_text = (
                f"{art['title']} {art['title']} {art['title']} "
                f"{art['keywords']} {art['keywords']} {art['keywords']} "
                f"{art['summary']} {art['summary']} "
                f"{art['content']}"
            )
            tokens = self._tokenize(weighted_text)
            art["tokens"] = tokens
            art["token_set"] = set(tokens)
            doc_lengths.append(len(tokens))

            # Count document frequencies
            for tok in art["token_set"]:
                df_counts[tok] = df_counts.get(tok, 0) + 1

            self._articles_cache.append(art)

        N = len(self._articles_cache)
        if N > 0:
            self._avg_doc_len = sum(doc_lengths) / N
            # BM25-style IDF calculation
            for tok, df in df_counts.items():
                self._idf_cache[tok] = math.log(1.0 + (N - df + 0.5) / (df + 0.5))

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Searches the local knowledge base and returns top-k ranked documents.
        """
        if not self._articles_cache:
            self._load_and_index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Parameters for BM25
        k1 = 1.5
        b = 0.75

        scores = []
        for art in self._articles_cache:
            if category and art["category"].lower() != category.lower():
                # Allow cross-category if query has strong exact match, otherwise penalize
                cat_multiplier = 0.3
            else:
                cat_multiplier = 1.0

            doc_tokens = art["tokens"]
            doc_len = len(doc_tokens)
            if doc_len == 0:
                continue

            # Frequency map for current document
            tf_map: Dict[str, int] = {}
            for t in doc_tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            bm25_score = 0.0
            query_set = set(query_tokens)
            matched_terms = 0

            for q_tok in query_tokens:
                if q_tok in tf_map:
                    matched_terms += 1
                    freq = tf_map[q_tok]
                    idf = self._idf_cache.get(q_tok, 0.5)
                    numerator = freq * (k1 + 1)
                    denominator = freq + k1 * (1 - b + b * (doc_len / (self._avg_doc_len or 1)))
                    bm25_score += idf * (numerator / denominator)

            # Bonus for matching title or keywords exactly
            query_str_clean = query.lower()
            if any(kw.strip().lower() in query_str_clean for kw in art["keywords"].split(",") if kw.strip()):
                bm25_score += 4.0
            if any(w in art["title"].lower() for w in query_tokens):
                bm25_score += 2.0

            # Normalize to ~ 0.0 - 1.0
            norm_score = min(1.0, (bm25_score * cat_multiplier) / 12.0)

            if norm_score > 0.05:
                # Extract relevant snippet
                snippet = self._extract_snippet(art["content"], query_tokens)
                scores.append({
                    "article_id": art["article_id"],
                    "category": art["category"],
                    "title": art["title"],
                    "policy_code": art["policy_code"],
                    "score": round(norm_score, 3),
                    "snippet": snippet,
                    "full_content": art["content"]
                })

        # Sort descending by score
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def _extract_snippet(self, content: str, query_tokens: List[str]) -> str:
        """Finds the most relevant paragraph containing query tokens."""
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        best_p = paragraphs[0] if paragraphs else ""
        best_overlap = -1

        q_set = set(query_tokens)
        for p in paragraphs:
            p_tokens = set(self._tokenize(p))
            overlap = len(p_tokens.intersection(q_set))
            if overlap > best_overlap:
                best_overlap = overlap
                best_p = p

        # Truncate snippet if too long
        lines = best_p.splitlines()
        clean_lines = [l for l in lines if not l.startswith("#")]
        result = " ".join(clean_lines)
        if len(result) > 300:
            result = result[:297] + "..."
        return result or best_p[:300]

# Global singleton
retriever = LocalKnowledgeRetriever()
