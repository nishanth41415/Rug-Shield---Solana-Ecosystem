"""
scorer.py — RugShield P2 final scoring pipeline.

Takes any Solana token mint address, runs all 18 signals + ML model,
and outputs a complete 0–100 risk score JSON.

Usage:
    python3 scorer.py <token_address>
    python3 scorer.py EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v   # USDC (should be LOW)

Fixed from original:
    - Deployer wallet is now fetched FIRST from real on-chain data,
      then passed to graph signals (was incorrectly passing token_address as deployer)
    - Per-signal progress logging added
    - Error isolation: one failing signal never aborts the rest
"""

import json
import pickle
import re
import sys
import warnings
warnings.filterwarnings("ignore")

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE       = Path(__file__).parent
MODEL_PATH = BASE / "model" / "scorer.pkl"

sys.path.insert(0, str(BASE))

# ---------------------------------------------------------------------------
#  Signal weights — contribution of each signal to the final score
#  Higher weight = more important red flag
# ---------------------------------------------------------------------------

NEUTRAL_SCORE = 0.5

# Weight multiplier by data quality (mock/unavailable excluded from rule score)
SOURCE_WEIGHT_SCALE = {
    "real":        1.0,
    "fallback":    0.35,
    "mock":        0.0,
    "unavailable": 0.0,
}

SIGNAL_WEIGHTS = {
    "S01": 0.90,   # mint authority      — CRITICAL
    "S02": 0.70,   # freeze authority    — HIGH
    "S03": 0.60,   # upgradeable program — HIGH
    "S04": 0.50,   # metadata mutable    — MEDIUM
    "S05": 0.80,   # LP lock             — CRITICAL
    "S06": 0.75,   # deployer LP         — CRITICAL
    "S08": 0.65,   # top-10 holders      — HIGH
    "S09": 0.70,   # whale dominance     — HIGH
    "S10": 0.75,   # sybil clusters      — HIGH
    "S11": 0.90,   # rug history         — CRITICAL
    "S12": 0.80,   # wallet age          — CRITICAL
    "S13": 0.65,   # suspicious tx       — HIGH
    "S14": 0.60,   # bot spike           — HIGH
    "S15": 0.65,   # wash trading        — HIGH
    "S16": 0.85,   # insider dump        — CRITICAL
    "S17": 0.55,   # social verify       — MEDIUM
    "S18": 0.50,   # fake engagement     — MEDIUM
}


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

_BASE58_RE = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def is_valid_solana_address(address: str) -> bool:
    """Return True if address looks like a valid base58 Solana pubkey."""
    if not isinstance(address, str):
        return False
    address = address.strip()
    if not address or not _BASE58_RE.fullmatch(address):
        return False
    try:
        import base58
        return len(base58.b58decode(address)) == 32
    except ImportError:
        return True
    except Exception:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_model():
    if not MODEL_PATH.exists():
        print("[ERROR] ML model not found. Run:  python3 train_model.py")
        sys.exit(1)
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _risk_label(score: int) -> str:
    if score >= 80:   return "CRITICAL"
    elif score >= 60: return "HIGH"
    elif score >= 30: return "MEDIUM"
    else:             return "LOW"


def _recommendation(score: int) -> str:
    if score >= 80:
        return "DO NOT BUY. Extremely high probability of rug pull."
    elif score >= 60:
        return "HIGH RISK. Avoid unless you can verify all red flags manually."
    elif score >= 30:
        return "MEDIUM RISK. Proceed with caution and small position sizes only."
    else:
        return "LOW RISK. Token appears safe based on available on-chain signals."


# ---------------------------------------------------------------------------
#  Signal runner
# ---------------------------------------------------------------------------

def _run_all_signals(token_address: str, deployer_wallet: str) -> list[dict]:
    """
    Run all 18 signals and return their result dicts.

    Signal groups:
        S01–S09  — on-chain authority + holder signals (signals.py)
        S10–S13  — wallet graph signals (graph_signals.py)  ← needs deployer_wallet
        S14–S18  — behavioral + social signals (behavioral_signals.py)

    Each signal is wrapped in its own try/except so one failure
    never prevents the others from running.
    """
    from signals.signals           import run_all_signals      as run_base
    from signals.graph_signals     import run_graph_signals
    from signals.behavioral_signals import run_behavioral_signals

    results = []

    print("  [1/3] Running on-chain authority + holder signals (S01-S09)...")
    try:
        results += run_base(token_address)
    except Exception as e:
        print(f"        [ERROR] Base signals failed: {e}")

    print(f"  [2/3] Running wallet graph signals (S10-S13) for deployer {deployer_wallet[:8]}...")
    try:
        results += run_graph_signals(token_address, deployer_wallet=deployer_wallet)
    except Exception as e:
        print(f"        [ERROR] Graph signals failed: {e}")

    print("  [3/3] Running behavioral signals (S14-S18)...")
    try:
        results += run_behavioral_signals(token_address)
    except Exception as e:
        print(f"        [ERROR] Behavioral signals failed: {e}")

    return results


# ---------------------------------------------------------------------------
#  Data quality + verified-token adjustments
# ---------------------------------------------------------------------------

def _signal_source(sig: dict) -> str:
    src = sig.get("details", {}).get("data_source", "real")
    if src in ("dexscreener",):
        return "real"
    return src


def _has_real_critical_flags(signals: list[dict]) -> bool:
    """True when a real-data signal shows confirmed severe risk."""
    for sig in signals:
        if _signal_source(sig) != "real":
            continue
        if sig["signal_id"] == "S11" and sig["score"] >= 0.9:
            return True
    return False


def _apply_verified_token_adjustments(token_address: str, signals: list[dict]) -> list[dict]:
    """Reduce false positives for known major tokens — does not bypass scoring."""
    from config import get_verified_token_profile, score_to_risk

    profile = get_verified_token_profile(token_address)
    if not profile:
        return signals

    for sig in signals:
        sid = sig["signal_id"]
        src = _signal_source(sig)

        if profile.get("type") == "stablecoin" and sid in ("S01", "S02") and src == "real":
            sig["score"] = min(float(sig["score"]), 0.15)
            sig["risk_level"] = score_to_risk(sig["score"])
            sig["details"]["verified_adjustment"] = (
                f"{profile['symbol']}: mint/freeze authority expected for regulated stablecoin"
            )
        if profile.get("type") in ("stablecoin", "native_wrapped") and sid in ("S08", "S09"):
            if src in ("real", "mock"):
                sig["score"] = min(float(sig["score"]), 0.35)
                sig["risk_level"] = score_to_risk(sig["score"])
                sig["details"]["verified_adjustment"] = (
                    f"{profile['symbol']}: holder concentration normal for major token"
                )
        if sid == "S12" and src == "real" and sig.get("score") is not None:
            sig["score"] = min(float(sig["score"]), 0.15)
            sig["risk_level"] = score_to_risk(sig["score"])
            sig["details"]["verified_adjustment"] = (
                f"{profile['symbol']}: deployer-wallet age not indicative for established mint"
            )
    return signals


def _build_signal_quality(signals: list[dict]) -> dict:
    buckets: dict[str, list[str]] = {
        "real": [], "mock": [], "unavailable": [], "fallback": [],
    }
    for sig in signals:
        src = _signal_source(sig)
        buckets.setdefault(src, []).append(sig["signal_id"])

    real_count = len(buckets["real"])
    total = len(signals) or 1
    ratio = real_count / total

    if ratio >= 0.65:
        level = "high"
    elif ratio >= 0.35:
        level = "medium"
    else:
        level = "low"

    fallback_count = len(buckets["mock"]) + len(buckets["fallback"])

    return {
        "confidence_level": level,
        "confidence_score": round(ratio, 3),
        "real_signals_count":        len(buckets["real"]),
        "fallback_signals_count":    fallback_count,
        "unavailable_signals_count": len(buckets["unavailable"]),
        "signals_real":        buckets["real"],
        "signals_mock":        buckets["mock"],
        "signals_unavailable": buckets["unavailable"],
        "signals_fallback":    buckets["fallback"],
    }


# ---------------------------------------------------------------------------
#  Score computation
# ---------------------------------------------------------------------------

def _compute_score(signals: list[dict], ml_model) -> dict:
    """
    Blend rule-based weighted average with ML model probability.

    Formula:
        final_score (0–100) = round(
            (0.60 × weighted_signal_average + 0.40 × ml_probability) × 100
        )
    """
    total_weight = 0.0
    weighted_sum = 0.0
    signal_map   = {}

    for sig in signals:
        sid    = sig["signal_id"]
        src    = _signal_source(sig)
        raw    = sig.get("score")
        score  = float(raw) if raw is not None else NEUTRAL_SCORE
        base_w = SIGNAL_WEIGHTS.get(sid, 0.5)
        weight = base_w * SOURCE_WEIGHT_SCALE.get(src, 1.0)

        if weight > 0 and src == "real":
            weighted_sum += score * weight
            total_weight += weight

        signal_map[sid] = score if src == "real" else NEUTRAL_SCORE

    rule_score = weighted_sum / total_weight if total_weight > 0 else NEUTRAL_SCORE

    feature_order = [
        "S01", "S02", "S03", "S04", "S05", "S06",
        "S07",
        "S08", "S09", "S10", "S11", "S12", "S13",
        "S14", "S15", "S16", "S17", "S18",
    ]
    ml_features = []
    for sid in feature_order:
        src = next(( _signal_source(s) for s in signals if s["signal_id"] == sid), "real")
        val = signal_map.get(sid, NEUTRAL_SCORE)
        if src in ("mock", "unavailable"):
            val = NEUTRAL_SCORE
        ml_features.append(val)
    feature_names = getattr(ml_model, "feature_names_in_", None)
    if feature_names is not None:
        features = pd.DataFrame([ml_features], columns=list(feature_names))
    else:
        features = [ml_features]

    try:
        ml_prob = float(ml_model.predict_proba(features)[0][1])
    except Exception as e:
        print(f"  [WARN] ML model prediction failed ({e}) — using rule score as fallback")
        ml_prob = rule_score

    # Blend: 60% rule-based + 40% ML
    combined    = (0.60 * rule_score) + (0.40 * ml_prob)
    final_score = round(combined * 100)

    return {
        "final_score": final_score,
        "rule_score":  round(rule_score * 100, 1),
        "ml_score":    round(ml_prob    * 100, 1),
        "signal_scores": {
            sid: round(score * 100, 1)
            for sid, score in signal_map.items()
        },
    }


# ---------------------------------------------------------------------------
#  Main output builder
# ---------------------------------------------------------------------------

def score_token(token_address: str) -> dict:
    """
    Full scoring pipeline:
        1. Look up the real deployer wallet from on-chain data
        2. Run all 18 signals
        3. Blend with ML model
        4. Return complete JSON output
    """
    print(f"\n{'='*60}")
    print(f"  Scoring token: {token_address}")
    print(f"{'='*60}")

    # Step 1 — resolve deployer wallet (CRITICAL FIX: was using token_address before)
    print("  Resolving deployer wallet from on-chain data...")
    from solana_rpc import get_deployer_wallet
    deployer_wallet = get_deployer_wallet(token_address)
    print(f"  Deployer wallet: {deployer_wallet[:8]}...")

    # Step 2 — load ML model
    model = _load_model()

    # Step 3 — run all signals
    signals = _run_all_signals(token_address, deployer_wallet)

    if not signals:
        print("[ERROR] All signals failed — cannot produce a score.")
        sys.exit(1)

    signals = _apply_verified_token_adjustments(token_address, signals)
    quality = _build_signal_quality(signals)

    # Step 4 — compute score
    scores = _compute_score(signals, model)

    final = scores["final_score"]
    from config import get_verified_token_profile
    profile = get_verified_token_profile(token_address)
    if profile and not _has_real_critical_flags(signals):
        cap = profile.get("max_risk_score", 25)
        if final > cap:
            final = cap
            print(f"  [INFO] Verified token {profile.get('symbol')} — score capped at {cap}")

    risk = _risk_label(final)

    output = {
        "token_address":     token_address,
        "deployer_wallet":   deployer_wallet,
        "verified_token":    profile.get("symbol") if profile else None,
        "risk_score":        final,
        "risk_level":        risk,
        "recommendation":    _recommendation(final),
        "scoring_breakdown": {
            "rule_based_score": scores["rule_score"],
            "ml_model_score":   scores["ml_score"],
            "final_score":      final,
            "blend":            "60% rule-based + 40% ML model (real-data signals weighted)",
        },
        "signal_quality": quality,
        "signals": [
            {
                "signal_id":    s["signal_id"],
                "score":        s["score"],
                "risk_level":   s["risk_level"],
                "data_source":  _signal_source(s),
                "check":        s["details"]["check"],
                "explanation":  s["details"]["explanation"],
            }
            for s in signals
        ],
        "signals_run":  len(signals),
        "timestamp":    _now(),
    }

    return output


# ---------------------------------------------------------------------------
#  CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage:   python3 scorer.py <token_address>")
        print("Example: python3 scorer.py EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        sys.exit(1)

    from config import warn_if_missing_env
    warn_if_missing_env()

    token_address = sys.argv[1].strip()
    if not is_valid_solana_address(token_address):
        print(f"[ERROR] Invalid Solana token address: {token_address!r}")
        sys.exit(1)

    result = score_token(token_address)

    final = result["risk_score"]
    risk  = result["risk_level"]

    # Pretty console output
    print(f"\n{'='*60}")
    print(f"  RISK SCORE : {final} / 100")
    print(f"  RISK LEVEL : {risk}")
    print(f"  VERDICT    : {result['recommendation']}")
    print(f"{'='*60}")
    print(f"  Deployer   : {result['deployer_wallet'][:20]}...")
    print(f"  Rule-based : {result['scoring_breakdown']['rule_based_score']}")
    print(f"  ML model   : {result['scoring_breakdown']['ml_model_score']}")
    print(f"\n  Signal breakdown ({result['signals_run']} signals):")
    for sig in result["signals"]:
        if sig["score"] is None:
            print(f"    {sig['signal_id']}  n/a   {'':20}  {sig['risk_level']}")
        else:
            filled = int(sig["score"] * 20)
            bar = "█" * filled
            print(f"    {sig['signal_id']}  {sig['score']:.2f}  {bar:<20}  {sig['risk_level']}")

    # Save JSON output
    out_path = BASE / "output" / f"{token_address[:8]}_score.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Full JSON saved -> {out_path}")


if __name__ == "__main__":
    main()
