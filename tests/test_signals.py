"""
tests/test_signals.py — Unit tests for all signal implementations.

Run with:  python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from signals.signals import (
    signal_01_mint_authority,
    signal_02_freeze_authority,
    signal_03_upgradeable_contract,
    signal_04_metadata_mutability,
    signal_05_lp_lock_status,
    signal_06_deployer_lp_concentration,
    signal_08_top10_concentration,
    signal_09_whale_dominance,
    run_all_signals,
)
from config import score_to_risk

ADDRESS = "So11111111111111111111111111111111111111112"
REQUIRED_KEYS = {"signal_id", "token_address", "score", "risk_level", "details", "timestamp"}
REQUIRED_DETAIL_KEYS = {"check", "result", "explanation"}
VALID_RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


# --------------------------------------------------------------------------- #
#  Schema validation helper                                                    #
# --------------------------------------------------------------------------- #

def assert_valid_signal(result: dict, expected_id: str):
    assert isinstance(result, dict), "Result must be a dict"
    assert REQUIRED_KEYS == result.keys() | (REQUIRED_KEYS - result.keys()), \
        f"Missing keys: {REQUIRED_KEYS - result.keys()}"
    for k in REQUIRED_KEYS:
        assert k in result, f"Missing key: {k}"

    assert result["signal_id"] == expected_id
    assert result["token_address"] == ADDRESS
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 1.0, f"Score out of range: {result['score']}"
    assert result["risk_level"] in VALID_RISKS
    assert result["risk_level"] == score_to_risk(result["score"])

    details = result["details"]
    for k in REQUIRED_DETAIL_KEYS:
        assert k in details, f"Missing detail key: {k}"
    assert isinstance(details["explanation"], str)
    assert len(details["explanation"]) > 10


# --------------------------------------------------------------------------- #
#  Per-signal tests                                                            #
# --------------------------------------------------------------------------- #

def test_s01_schema():
    result = signal_01_mint_authority(ADDRESS)
    assert_valid_signal(result, "S01")

def test_s01_score_is_binary():
    result = signal_01_mint_authority(ADDRESS)
    assert result["score"] in (0.0, 0.9), f"S01 score should be 0.0 or 0.9, got {result['score']}"

def test_s02_schema():
    result = signal_02_freeze_authority(ADDRESS)
    assert_valid_signal(result, "S02")

def test_s02_score_is_binary():
    result = signal_02_freeze_authority(ADDRESS)
    assert result["score"] in (0.0, 0.7), f"S02 score should be 0.0 or 0.7, got {result['score']}"

def test_s03_schema():
    result = signal_03_upgradeable_contract(ADDRESS)
    assert_valid_signal(result, "S03")

def test_s04_schema():
    result = signal_04_metadata_mutability(ADDRESS)
    assert_valid_signal(result, "S04")

def test_s05_schema():
    result = signal_05_lp_lock_status(ADDRESS)
    assert_valid_signal(result, "S05")

def test_s05_score_inverse_of_lock():
    result = signal_05_lp_lock_status(ADDRESS)
    locked = result["details"]["result"]
    expected_score = round(1.0 - locked, 4)
    assert abs(result["score"] - expected_score) < 0.001

def test_s06_schema():
    result = signal_06_deployer_lp_concentration(ADDRESS)
    assert_valid_signal(result, "S06")

def test_s08_schema():
    result = signal_08_top10_concentration(ADDRESS)
    assert_valid_signal(result, "S08")

def test_s08_result_has_holders_list():
    result = signal_08_top10_concentration(ADDRESS)
    assert "holders" in result["details"]["result"]
    assert isinstance(result["details"]["result"]["holders"], list)

def test_s09_schema():
    result = signal_09_whale_dominance(ADDRESS)
    assert_valid_signal(result, "S09")

def test_s09_high_whale_is_critical():
    """Patch holder info to force a 60% whale → should be CRITICAL."""
    import signals.signals as sig_module

    original = sig_module.get_holder_info
    sig_module.get_holder_info = lambda _: {
        "top_10_concentration": 0.9,
        "top_holder_percent": 0.6,
        "holders": [0.6, 0.1, 0.05, 0.04, 0.03, 0.02, 0.02, 0.02, 0.01, 0.01],
    }
    try:
        result = signal_09_whale_dominance(ADDRESS)
        assert result["risk_level"] == "CRITICAL"
        assert result["score"] >= 0.8
    finally:
        sig_module.get_holder_info = original


# --------------------------------------------------------------------------- #
#  run_all_signals                                                             #
# --------------------------------------------------------------------------- #

def test_run_all_signals_returns_8():
    results = run_all_signals(ADDRESS)
    assert len(results) == 8

def test_run_all_signals_all_valid_schema():
    results = run_all_signals(ADDRESS)
    ids = [r["signal_id"] for r in results]
    assert ids == ["S01", "S02", "S03", "S04", "S05", "S06", "S08", "S09"]
    for r in results:
        assert r["token_address"] == ADDRESS
        assert 0.0 <= r["score"] <= 1.0
        assert r["risk_level"] in VALID_RISKS


# --------------------------------------------------------------------------- #
#  score_to_risk helper                                                        #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("score,expected", [
    (0.0, "LOW"),
    (0.15, "LOW"),
    (0.29, "LOW"),
    (0.3, "MEDIUM"),
    (0.5, "MEDIUM"),
    (0.59, "MEDIUM"),
    (0.6, "HIGH"),
    (0.75, "HIGH"),
    (0.79, "HIGH"),
    (0.8, "CRITICAL"),
    (0.95, "CRITICAL"),
    (1.0, "CRITICAL"),
])
def test_score_to_risk(score, expected):
    assert score_to_risk(score) == expected
