"""
tests/test_e2e.py — End-to-end confidence tests for the scoring pipeline.

Run with:  python -m pytest tests/test_e2e.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from scorer import is_valid_solana_address, score_token

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WRAPPED_SOL = "So11111111111111111111111111111111111111112"


def test_is_valid_solana_address():
    assert not is_valid_solana_address("")
    assert not is_valid_solana_address("   ")
    assert not is_valid_solana_address("not_a_valid_address")
    assert is_valid_solana_address(WRAPPED_SOL)
    assert is_valid_solana_address(USDC)


def test_db_health_check_returns_bool():
    from graph_analyzer.graph_analyzer import check_db_connection
    assert isinstance(check_db_connection(), bool)


def test_full_pipeline_wrapped_sol():
    result = score_token(WRAPPED_SOL)
    assert result["token_address"] == WRAPPED_SOL
    assert "risk_score" in result
    assert "risk_level" in result
    assert "signals" in result
    assert result["signals_run"] == 17   # S07 intentionally skipped
    assert len(result["signals"]) == 17
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_full_pipeline_has_required_fields():
    result = score_token(USDC)
    required = {
        "token_address", "deployer_wallet", "risk_score", "risk_level",
        "recommendation", "scoring_breakdown", "signals", "signals_run", "timestamp",
    }
    assert required.issubset(result.keys())
    assert result["signals_run"] == 17   # S07 intentionally skipped
