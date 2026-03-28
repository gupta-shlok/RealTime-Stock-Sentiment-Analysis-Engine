"""
Integration tests for SENT-03, SENT-04, SENT-05 endpoints.
Tests use TestClient with mocked filesystem helpers.
No real model inference occurs — lifespan is bypassed via dependency overrides.

Run: pytest backend/tests/test_endpoints.py -x -q
"""
import pytest
import json
import sys
import os
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We need to bypass the lifespan (model loading) for TestClient.
# Strategy: mock the model loading functions at import time, then patch
# _load_scores_file and _load_narratives_file per test.


# Sample data fixtures
SAMPLE_SCORES = {
    "AAPL": {
        "2026-03-28": 0.34,
        "2026-03-27": 0.21,
        "2026-03-26": 0.15,
        "2026-03-25": 0.08,
        "2026-03-24": -0.05,
        "2026-03-23": 0.12,
        "2026-03-22": 0.19,
    },
    "MSFT": {"2026-03-28": 0.22},
    "NVDA": {"2026-03-28": 0.41},
    "GOOGL": {"2026-03-28": 0.18},
    # Enough Technology tickers for stock_count >= 3
}

SAMPLE_NARRATIVES_FRESH = {
    "AAPL": {
        "narrative": "Apple's positive sentiment is driven by headline #1 [+0.41] reporting record iPhone sales.",
        "generated_at": "2099-01-01T00:00:00+00:00",  # Far future = always fresh
        "headlines_used": 8,
    }
}

SAMPLE_NARRATIVES_EMPTY = {}


@pytest.fixture(scope="module")
def mock_app_state():
    """Mock app.state so TestClient doesn't trigger real model loading."""
    import torch
    state = MagicMock()
    state.finbert_model = MagicMock()
    state.finbert_model.device = torch.device("cpu")
    state.finbert_tokenizer = MagicMock()
    state.qwen_model = MagicMock()
    state.qwen_tokenizer = MagicMock()
    return state


@pytest.fixture(scope="module")
def test_client(mock_app_state):
    """TestClient that bypasses lifespan model loading."""
    # We patch AutoModelForSequenceClassification and AutoModelForCausalLM to prevent
    # actual model downloads during the TestClient context.
    with patch("main.AutoModelForSequenceClassification") as mock_finbert_cls, \
         patch("main.AutoModelForCausalLM") as mock_qwen_cls, \
         patch("main.AutoTokenizer") as mock_tok_cls, \
         patch("main.asyncio.create_task"):  # prevent background tasks

        import torch
        # Make lifespan model loading succeed with mocks
        mock_finbert_model = MagicMock()
        mock_finbert_model.device = torch.device("cpu")
        mock_output = MagicMock()
        mock_output.logits = torch.tensor([[0.7, 0.1, 0.2]])
        mock_finbert_model.return_value = mock_output
        mock_finbert_model.eval.return_value = None

        mock_finbert_cls.from_pretrained.return_value = mock_finbert_model

        mock_qwen_model = MagicMock()
        mock_qwen_model.device = torch.device("cpu")
        # generate() returns token ids
        mock_qwen_model.generate.return_value = torch.zeros(1, 15, dtype=torch.long)
        mock_qwen_cls.from_pretrained.return_value = mock_qwen_model

        mock_tokenizer = MagicMock()
        dummy_inputs = MagicMock()
        dummy_inputs.to = lambda d: {"input_ids": torch.zeros(1, 5, dtype=torch.long), "attention_mask": torch.ones(1, 5, dtype=torch.long)}
        dummy_inputs.__getitem__ = lambda self, key: {"input_ids": torch.zeros(1, 5, dtype=torch.long)}[key]
        mock_tokenizer.return_value = dummy_inputs
        mock_tokenizer.apply_chat_template.return_value = "dummy prompt"
        mock_tokenizer.decode.return_value = "warm-up"
        mock_tokenizer.eos_token_id = 2
        mock_tok_cls.from_pretrained.return_value = mock_tokenizer

        import main
        from main import require_api_key
        main.app.dependency_overrides[require_api_key] = lambda: None  # bypass API key auth in tests
        with TestClient(main.app) as client:
            yield client
        main.app.dependency_overrides.clear()


# ─── SENT-03: /sentiment-trends ──────────────────────────────────────────────

def test_sentiment_trends_7d(test_client):
    """SENT-03: 7d window returns EMA-smoothed data with span=5."""
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sentiment-trends?ticker=AAPL&window=7d")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["window"] == "7d"
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert "date" in body["data"][0]
    assert "score" in body["data"][0]


def test_sentiment_trends_30d(test_client):
    """SENT-03: 30d window returns EMA span=20; window field is '30d'."""
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sentiment-trends?ticker=AAPL&window=30d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["window"] == "30d"
    assert isinstance(body["data"], list)


def test_sentiment_trends_invalid_window(test_client):
    """SENT-03: Invalid window returns HTTP 400."""
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sentiment-trends?ticker=AAPL&window=invalid")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"


def test_sentiment_trends_unknown_ticker(test_client):
    """SENT-03: Unknown ticker returns empty data list, not 404."""
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sentiment-trends?ticker=ZZZZ&window=7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []


# ─── SENT-04: /sector-sentiment ──────────────────────────────────────────────

def test_sector_sentiment_inclusion(test_client):
    """SENT-04: Sectors with >= 3 scored stocks appear in response."""
    # SAMPLE_SCORES has AAPL, MSFT, NVDA — all in Technology (3 tickers at threshold)
    # stock_count counts how many constituent tickers HAVE scores, not total tickers.
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sector-sentiment")
    assert resp.status_code == 200
    body = resp.json()
    assert "Technology" in body, f"Technology missing from {list(body.keys())}"
    assert body["Technology"]["stock_count"] >= 3


def test_sector_sentiment_exclusion(test_client):
    """SENT-04: Real Estate has only 2 tickers in tickers.py — must be excluded."""
    # Even if both Real Estate tickers (EQIX, SPG) have scores, stock_count=2 < 3
    scores_with_real_estate = {
        **SAMPLE_SCORES,
        "EQIX": {"2026-03-28": 0.10},
        "SPG": {"2026-03-28": -0.05},
    }
    with patch("main._load_scores_file", return_value=scores_with_real_estate):
        resp = test_client.get("/sector-sentiment")
    assert resp.status_code == 200
    body = resp.json()
    assert "Real Estate" not in body, f"Real Estate should be excluded but got stock_count={body.get('Real Estate')}"


def test_sector_sentiment_response_shape(test_client):
    """SENT-04: Each sector entry has 'score' (float) and 'stock_count' (int)."""
    with patch("main._load_scores_file", return_value=SAMPLE_SCORES):
        resp = test_client.get("/sector-sentiment")
    assert resp.status_code == 200
    body = resp.json()
    for sector, data in body.items():
        assert "score" in data, f"Sector '{sector}' missing 'score'"
        assert "stock_count" in data, f"Sector '{sector}' missing 'stock_count'"
        assert isinstance(data["score"], (int, float)), f"score must be numeric for '{sector}'"
        assert isinstance(data["stock_count"], int), f"stock_count must be int for '{sector}'"
        assert data["stock_count"] >= 3, f"stock_count must be >= 3 for '{sector}', got {data['stock_count']}"


# ─── SENT-05: /stock-narrative/{ticker} ──────────────────────────────────────

def test_narrative_cache_hit(test_client):
    """SENT-05: Fresh cached narrative returns status:'complete' immediately."""
    with patch("main._load_narratives_file", return_value=SAMPLE_NARRATIVES_FRESH):
        resp = test_client.get("/stock-narrative/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete", f"Expected complete, got: {body}"
    assert "narrative" in body
    assert body["ticker"] == "AAPL"
    assert "generated_at" in body
    assert "headlines_used" in body


def test_narrative_pending(test_client):
    """SENT-05: No cached narrative returns status:'pending' with UUID job_id."""
    with patch("main._load_narratives_file", return_value=SAMPLE_NARRATIVES_EMPTY):
        resp = test_client.get("/stock-narrative/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending", f"Expected pending, got: {body}"
    assert "job_id" in body
    # Validate UUID format
    try:
        uuid.UUID(body["job_id"])
    except ValueError:
        pytest.fail(f"job_id is not a valid UUID: {body['job_id']}")


def test_narrative_unknown_ticker_enqueues(test_client):
    """SENT-05: Unknown ticker with no narrative -> returns pending status."""
    with patch("main._load_narratives_file", return_value=SAMPLE_NARRATIVES_EMPTY):
        resp = test_client.get("/stock-narrative/UNKNOWN_TICKER_XYZ")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert "job_id" in body
