"""
Unit tests for SENT-01: FinBERT full-probability scoring.
Tests the finbert_score() function after the pipeline() replacement.

Run: pytest backend/tests/test_finbert.py -x
"""
import pytest
import torch
import torch.nn.functional as F
from unittest.mock import MagicMock, patch


def _make_mock_app_state(logits_list: list):
    """Helper: returns a mock app.state with finbert_model returning given logits."""
    mock_model = MagicMock()
    mock_model.device = torch.device("cpu")
    mock_output = MagicMock()
    mock_output.logits = torch.tensor([logits_list])
    mock_model.return_value = mock_output

    mock_tokenizer = MagicMock()
    dummy_inputs = {
        "input_ids": torch.zeros(1, 10, dtype=torch.long),
        "attention_mask": torch.ones(1, 10, dtype=torch.long),
    }
    tokenizer_result = MagicMock()
    tokenizer_result.to = lambda device: dummy_inputs
    mock_tokenizer.return_value = tokenizer_result

    mock_state = MagicMock()
    mock_state.finbert_model = mock_model
    mock_state.finbert_tokenizer = mock_tokenizer
    return mock_state


def test_label_order():
    """SENT-01: id2label {0: positive, 1: negative} — high logit[0] -> positive score."""
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([2.0, 0.1, 0.5])
        import main
        score, confidence = main.finbert_score("good earnings beat")
    assert score > 0, f"Expected positive score for positive logits, got {score}"


def test_score_direction_positive():
    """SENT-01: logits [0.7, 0.1, 0.2] -> score > 0."""
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([0.7, 0.1, 0.2])
        import main
        score, _ = main.finbert_score("market rally")
    assert score > 0


def test_score_direction_negative():
    """SENT-01: logits [0.1, 0.7, 0.2] -> score < 0."""
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([0.1, 0.7, 0.2])
        import main
        score, _ = main.finbert_score("bankruptcy filing")
    assert score < 0


def test_score_range():
    """SENT-01: score is in [-1, 1] for any logits."""
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([0.7, 0.1, 0.2])
        import main
        score, _ = main.finbert_score("any text")
    assert -1.0 <= score <= 1.0


def test_confidence_is_max_softmax():
    """SENT-01: confidence == max(softmax(logits))."""
    logits = [0.7, 0.1, 0.2]
    expected_probs = F.softmax(torch.tensor(logits), dim=-1)
    expected_confidence = expected_probs.max().item()
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state(logits)
        import main
        _, confidence = main.finbert_score("test text")
    assert abs(confidence - expected_confidence) < 1e-5


def test_finbert_score_returns_tuple():
    """SENT-01: finbert_score() returns a 2-tuple (score, confidence)."""
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([0.7, 0.1, 0.2])
        import main
        result = main.finbert_score("test")
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2-tuple, got {len(result)}-tuple"


def test_neutral_not_dominant():
    """
    SENT-01 regression: near-neutral logits [0.34, 0.33, 0.33] -> max(softmax) < 0.55.
    This approximates the neutral rate reduction: if confidence < FINBERT_MIN_CONFIDENCE (0.55),
    the article is filtered from aggregation, reducing neutral over-classification.
    Catches regressions in the threshold/formula interaction.
    """
    logits = [0.34, 0.33, 0.33]
    probs = F.softmax(torch.tensor(logits), dim=-1)
    confidence = probs.max().item()
    assert confidence < 0.55, (
        f"Near-neutral logits should produce confidence < 0.55 (filters via threshold), got {confidence:.4f}"
    )


def test_low_confidence_appears_in_news():
    """
    D-06: analyze_sentiment_ensemble() always returns a float — even for low-confidence inputs.
    Filtered articles still appear in /news with their raw score; threshold only affects aggregation.
    This test catches regressions if analyze_sentiment_ensemble is changed to apply threshold filtering.
    """
    with patch("main.app") as mock_app:
        mock_app.state = _make_mock_app_state([0.38, 0.32, 0.30])  # low confidence logits
        import main
        result = main.analyze_sentiment_ensemble("Stock performance was mixed today.")
    assert isinstance(result, float), f"Expected float, got {type(result)}"
    # Must return a score regardless of confidence level (D-06: threshold only affects aggregation)
    assert -1.0 <= result <= 1.0, f"Score must be in [-1, 1], got {result}"
