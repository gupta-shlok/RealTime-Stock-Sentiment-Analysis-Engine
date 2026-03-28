"""
Unit tests for SENT-01: FinBERT full-probability scoring.
Tests the finbert_score() function after the pipeline() replacement.

Run: pytest backend/tests/test_finbert.py -x
"""
import pytest
import torch
import torch.nn.functional as F
from unittest.mock import patch, MagicMock


# --- SENT-01: label order verification ---

def test_label_order():
    """
    SENT-01: ProsusAI/finbert id2label is {0: positive, 1: negative, 2: neutral}.
    Verify that logits [high, low, low] -> positive score (probs[0] > probs[1]).
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_score_direction_positive():
    """
    SENT-01: logits strongly positive [0.7, 0.1, 0.2] -> score > 0.
    score = P(positive) - P(negative) must be positive.
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_score_direction_negative():
    """
    SENT-01: logits strongly negative [0.1, 0.7, 0.2] -> score < 0.
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_score_range():
    """
    SENT-01: returned score is in [-1, 1].
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_confidence_is_max_softmax():
    """
    SENT-01: returned confidence == max(softmax(logits)).
    Used as weight in SENT-02 aggregation.
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_finbert_score_returns_tuple():
    """
    SENT-01: finbert_score() returns (score: float, confidence: float) -- not a bare float.
    All callers in Plan 02 must unpack this tuple.
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_neutral_not_dominant():
    """
    SENT-01 regression: near-neutral logits [0.34, 0.33, 0.33] -> max(softmax) < 0.55.
    Approximates neutral rate reduction: low-confidence articles are filtered by aggregate threshold.
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")


def test_low_confidence_appears_in_news():
    """
    D-06: analyze_sentiment_ensemble() always returns a float for any confidence level.
    Filtered articles still appear in /news with raw score (threshold only affects aggregation).
    """
    pytest.skip("Stub -- implement after Plan 02 replaces finbert_score()")
