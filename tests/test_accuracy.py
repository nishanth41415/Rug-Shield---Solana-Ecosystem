"""
tests/test_accuracy.py — Scoring accuracy and data-quality tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from scorer import is_valid_solana_address, score_token
from signals.behavioral_signals import (
    run_behavioral_signals,
    signal_17_social_verification,
    signal_18_fake_engagement_nlp,
)
from graph_analyzer.graph_analyzer import check_db_connection

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WRAPPED_SOL = "So11111111111111111111111111111111111111112"


def test_invalid_address_rejected():
    assert not is_valid_solana_address("")
    assert not is_valid_solana_address("not_a_valid_address")


def test_missing_db_does_not_crash():
    assert isinstance(check_db_connection(), bool)


def test_social_signals_neutral_without_api_keys(monkeypatch):
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    import config
    monkeypatch.setattr(config, "TWITTER_BEARER_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")

    s17 = signal_17_social_verification(USDC)
    assert s17["details"]["data_source"] == "unavailable"
    assert s17["score"] is None
    assert s17["risk_level"] == "UNAVAILABLE"

    s18 = signal_18_fake_engagement_nlp(USDC)
    assert s18["details"]["data_source"] == "unavailable"
    assert s18["score"] is None
    assert s18["risk_level"] == "UNAVAILABLE"


def test_behavioral_unavailable_not_medium_risk():
    """S14–S18 without live data must not present as MEDIUM risk evidence."""
    results = run_behavioral_signals(USDC)
    assert len(results) == 5
    for sig in results:
        if sig["details"]["data_source"] == "unavailable":
            assert sig["risk_level"] == "UNAVAILABLE"
            assert sig["score"] is None
            assert sig["risk_level"] not in ("MEDIUM", "HIGH", "CRITICAL")


def test_usdc_risk_not_high():
    result = score_token(USDC)
    assert result["risk_level"] in ("LOW", "MEDIUM")
    assert result["risk_score"] <= 30
    assert result["verified_token"] == "USDC"
    assert "signal_quality" in result
    q = result["signal_quality"]
    assert q["confidence_level"] in ("low", "medium", "high")
    assert q["unavailable_signals_count"] >= 2
    assert "S17" in q["signals_unavailable"]
    assert "S18" in q["signals_unavailable"]
    for sig in result["signals"]:
        if sig["signal_id"] in ("S14", "S15", "S16", "S17", "S18"):
            if sig["data_source"] == "unavailable":
                assert sig["risk_level"] == "UNAVAILABLE"
                assert sig["score"] is None


def test_fallback_signals_reduce_confidence():
    result = score_token(USDC)
    q = result["signal_quality"]
    assert q["unavailable_signals_count"] + q["fallback_signals_count"] >= 1
    assert q["real_signals_count"] < result["signals_run"]
    assert q["confidence_score"] < 1.0


def test_wrapped_sol_low_or_medium():
    result = score_token(WRAPPED_SOL)
    assert result["risk_level"] in ("LOW", "MEDIUM")
    assert result["risk_score"] <= 35
