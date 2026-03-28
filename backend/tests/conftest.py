"""
Shared fixtures for Phase 4 tests.
All fixtures mock model inference — no real FinBERT or Qwen loads during test runs.
"""
import pytest
import json
import os
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Fixed logits for a "strongly positive" article: [pos=0.7, neg=0.1, neu=0.2]
# After softmax these become approximately [0.627, 0.186, 0.209] -> score ~ +0.441, confidence ~ 0.627
MOCK_LOGITS_POSITIVE = [0.7, 0.1, 0.2]

# Fixed logits for a "strongly negative" article: [pos=0.1, neg=0.7, neu=0.2]
MOCK_LOGITS_NEGATIVE = [0.1, 0.7, 0.2]

# Fixed logits for a "low confidence / near-neutral" article: [pos=0.38, neg=0.32, neu=0.30]
MOCK_LOGITS_LOW_CONFIDENCE = [0.38, 0.32, 0.30]


@pytest.fixture(scope="session")
def mock_finbert_model():
    """Mock AutoModelForSequenceClassification that returns controllable logits."""
    import torch
    model = MagicMock()
    model.device = torch.device("cpu")
    # Default: return positive logits; tests can override output.logits directly
    mock_output = MagicMock()
    mock_output.logits = torch.tensor([MOCK_LOGITS_POSITIVE])
    model.return_value = mock_output
    return model


@pytest.fixture(scope="session")
def mock_finbert_tokenizer():
    """Mock AutoTokenizer that returns dummy input tensors."""
    import torch
    tokenizer = MagicMock()
    dummy_inputs = {
        "input_ids": torch.zeros(1, 10, dtype=torch.long),
        "attention_mask": torch.ones(1, 10, dtype=torch.long),
    }
    # tokenizer(text, ...) returns dummy inputs
    tokenizer.return_value = MagicMock(**{
        "to": lambda device: dummy_inputs,
        "input_ids": dummy_inputs["input_ids"],
        "attention_mask": dummy_inputs["attention_mask"],
    })
    return tokenizer


@pytest.fixture(scope="session")
def sample_scores_data():
    """Pre-built sentiment_scores.json content for endpoint tests."""
    return {
        "AAPL": {
            "2026-03-28": 0.34,
            "2026-03-27": 0.21,
            "2026-03-26": 0.15,
            "2026-03-25": 0.08,
            "2026-03-24": -0.05,
            "2026-03-23": 0.12,
            "2026-03-22": 0.19,
        },
        # Technology sector (>= 3 tickers): AAPL, MSFT, NVDA, GOOGL, META
        "MSFT": {"2026-03-28": 0.22},
        "NVDA": {"2026-03-28": 0.41},
        # Real Estate sector (< 3 tickers -- should be excluded): only 2 tickers exist in tickers.py
        # These will be populated dynamically in the test using SECTOR_TICKERS
    }


@pytest.fixture(scope="session")
def sample_narratives_data():
    """Pre-built narratives.json content -- used for cache-hit test."""
    return {
        "AAPL": {
            "narrative": "Apple's sentiment is driven by strong iPhone demand signals.",
            "generated_at": "2099-01-01T00:00:00+00:00",  # Far future = always fresh
            "headlines_used": 8,
        }
    }
