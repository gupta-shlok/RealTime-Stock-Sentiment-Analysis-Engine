"""
Unit tests for SENT-02: confidence-weighted mean aggregation with threshold filtering.

Run: pytest backend/tests/test_aggregation.py -x
"""
import pytest


# --- SENT-02: weighted mean ---

def test_weighted_mean_basic():
    """
    SENT-02: Two articles -- high-confidence bearish outweighs low-confidence bullish.
    articles = [{"score": -0.8, "confidence": 0.9}, {"score": 0.6, "confidence": 0.3}]
    Expected: (-0.8*0.9 + 0.6*0.3) / (0.9 + 0.3) = (-0.72 + 0.18) / 1.2 = -0.45
    """
    pytest.skip("Stub -- implement after Plan 02 adds aggregate_daily_score()")


def test_weighted_mean_equal_confidence():
    """
    SENT-02: Equal-confidence articles -> simple mean.
    articles = [{"score": 0.4, "confidence": 0.7}, {"score": -0.2, "confidence": 0.7}]
    Expected: (0.4 + -0.2) / 2 = 0.1
    """
    pytest.skip("Stub -- implement after Plan 02 adds aggregate_daily_score()")


def test_all_below_threshold():
    """
    SENT-02 + D-04: All articles below FINBERT_MIN_CONFIDENCE (0.55) -> returns None (day skipped).
    articles = [{"score": 0.5, "confidence": 0.40}, {"score": -0.3, "confidence": 0.45}]
    Expected: None
    """
    pytest.skip("Stub -- implement after Plan 02 adds aggregate_daily_score()")


def test_partial_threshold_filter():
    """
    SENT-02 + D-04: Mixed confidence -- only articles >= 0.55 are included.
    articles = [{"score": 0.8, "confidence": 0.80}, {"score": -0.5, "confidence": 0.40}]
    Expected: 0.8 (only the first article passes threshold)
    """
    pytest.skip("Stub -- implement after Plan 02 adds aggregate_daily_score()")


def test_empty_articles_returns_none():
    """
    SENT-02: Empty article list -> returns None.
    """
    pytest.skip("Stub -- implement after Plan 02 adds aggregate_daily_score()")


def test_scoring_cycle_groups_and_aggregates():
    """
    SENT-02 integration: _run_scoring_cycle() groups news by (ticker, date), scores articles,
    and writes sentiment_scores.json. This is the data source for all Plan 03 endpoint tests.
    """
    pytest.skip("Stub -- implement after Plan 02 adds _run_scoring_cycle()")
