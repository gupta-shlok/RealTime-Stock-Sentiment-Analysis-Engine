"""
Unit tests for SENT-02: confidence-weighted mean aggregation with threshold filtering.

Run: pytest backend/tests/test_aggregation.py -x
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest.mock import patch, MagicMock


# --- SENT-02: weighted mean ---

def test_weighted_mean_basic():
    """
    SENT-02: Two articles -- high-confidence bearish outweighs lower-confidence bullish.
    Both articles pass the 0.55 threshold (confidence 0.9 and 0.6 respectively).
    articles = [{"score": -0.8, "confidence": 0.9}, {"score": 0.6, "confidence": 0.6}]
    Expected: (-0.8*0.9 + 0.6*0.6) / (0.9 + 0.6) = (-0.72 + 0.36) / 1.5 = -0.24
    """
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(finbert_min_confidence=0.55)
        import main
        result = main.aggregate_daily_score([
            {"score": -0.8, "confidence": 0.9},
            {"score": 0.6, "confidence": 0.6},
        ])
    # (-0.8*0.9 + 0.6*0.6) / (0.9 + 0.6) = (-0.72 + 0.36) / 1.5 = -0.24
    assert result is not None
    assert abs(result - (-0.24)) < 1e-6


def test_weighted_mean_equal_confidence():
    """
    SENT-02: Equal-confidence articles -> simple mean.
    articles = [{"score": 0.4, "confidence": 0.7}, {"score": -0.2, "confidence": 0.7}]
    Expected: (0.4 + -0.2) / 2 = 0.1
    """
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(finbert_min_confidence=0.55)
        import main
        result = main.aggregate_daily_score([
            {"score": 0.4, "confidence": 0.7},
            {"score": -0.2, "confidence": 0.7},
        ])
    # (0.4 + -0.2) / 2 = 0.1
    assert result is not None
    assert abs(result - 0.1) < 1e-6


def test_all_below_threshold():
    """
    SENT-02 + D-04: All articles below FINBERT_MIN_CONFIDENCE (0.55) -> returns None (day skipped).
    articles = [{"score": 0.5, "confidence": 0.40}, {"score": -0.3, "confidence": 0.45}]
    Expected: None
    """
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(finbert_min_confidence=0.55)
        import main
        result = main.aggregate_daily_score([
            {"score": 0.5, "confidence": 0.40},
            {"score": -0.3, "confidence": 0.45},
        ])
    assert result is None


def test_partial_threshold_filter():
    """
    SENT-02 + D-04: Mixed confidence -- only articles >= 0.55 are included.
    articles = [{"score": 0.8, "confidence": 0.80}, {"score": -0.5, "confidence": 0.40}]
    Expected: 0.8 (only the first article passes threshold)
    """
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(finbert_min_confidence=0.55)
        import main
        result = main.aggregate_daily_score([
            {"score": 0.8, "confidence": 0.80},
            {"score": -0.5, "confidence": 0.40},  # below threshold
        ])
    assert result is not None
    assert abs(result - 0.8) < 1e-6


def test_empty_articles_returns_none():
    """
    SENT-02: Empty article list -> returns None.
    """
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(finbert_min_confidence=0.55)
        import main
        result = main.aggregate_daily_score([])
    assert result is None


def test_scoring_cycle_groups_and_aggregates():
    """
    SENT-02 integration: _run_scoring_cycle() reads news_cache, groups by (ticker, date),
    scores articles, and writes sentiment_scores.json with correct aggregated values.
    This is the data source for all Plan 03 endpoint tests.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from unittest.mock import patch, MagicMock, call
    import main

    fake_news = [
        {"ticker": "AAPL", "publishTime": "2026-03-28 10:00:00", "title": "Apple beats earnings"},
        {"ticker": "AAPL", "publishTime": "2026-03-28 11:00:00", "title": "iPhone demand strong"},
        {"ticker": "MSFT", "publishTime": "2026-03-28 09:00:00", "title": "Microsoft cloud grows"},
    ]

    # Mock finbert_score to return fixed values; mock _write_json_atomic to capture output
    with patch("main.news_cache", new={"news": fake_news}), \
         patch("main.finbert_score", return_value=(0.50, 0.80)) as mock_score, \
         patch("main._write_json_atomic") as mock_write, \
         patch("main._load_scores_file", return_value={}), \
         patch("main.get_settings", return_value=MagicMock(finbert_min_confidence=0.55)):

        main._run_scoring_cycle()

    # finbert_score called once per article title (3 articles)
    assert mock_score.call_count == 3, f"Expected 3 finbert_score calls, got {mock_score.call_count}"

    # _write_json_atomic called once with the SCORES_FILE path
    mock_write.assert_called_once()
    write_path, written_data = mock_write.call_args[0]
    assert write_path == main.SCORES_FILE, f"Wrong output path: {write_path}"

    # AAPL and MSFT should both appear in the written data
    assert "AAPL" in written_data, f"AAPL missing from written data: {list(written_data.keys())}"
    assert "MSFT" in written_data, f"MSFT missing from written data: {list(written_data.keys())}"

    # AAPL has 2 articles on 2026-03-28 — aggregated score should be a float
    assert "2026-03-28" in written_data["AAPL"], "Expected 2026-03-28 entry for AAPL"
    assert isinstance(written_data["AAPL"]["2026-03-28"], float), "Expected float score for AAPL"
