import pytest
from app.services.retriever import retriever
from seed_data import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database()

def test_retrieval_ont_red_light():
    results = retriever.search(query="blinking red optical light on ont box", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-CONN-01"
    assert "Fibre ONT Red Optical" in top["title"]
    assert top["score"] > 0.3

def test_retrieval_esim_activation():
    results = retriever.search(query="how to scan qr code for esim activation on iphone", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] == "KB-MOB-01"
    assert "eSIM" in top["title"]

def test_retrieval_refund_policy():
    results = retriever.search(query="courtesy credit refund policy threshold", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["article_id"] in ["KB-BILL-02", "KB-BILL-01"]
