"""
scorer.py — Final scoring pipeline.

Takes a token mint address, runs all 18 signals + ML model,
outputs a complete 0-100 risk score JSON.

Usage:
    python3 scorer.py <token_address>
    python3 scorer.py So11111111111111111111111111111111111111112
"""

import json
import pickle
import sys
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone
from pathlib import Path

BASE       = Path(__file__).parent
MODEL_PATH = BASE / "model" / "scorer.pkl"

sys.path.insert(0, str(BASE))

# Signal weights — how much each signal contributes to the final score
# Higher weight = more important signal
SIGNAL_WEIGHTS = {
    "S01": 0.90,   # mint authority      — critical
    "S02": 0.70,   # freeze authority    — high
    "S03": 0.60,   # upgradeable         — high
    "S04": 0.50,   # metadata mutable    — medium
    "S05": 0.80,   # LP lock             — critical
    "S06": 0.75,   # deployer LP         — critical
    "S08": 0.65,   # top 10 holders      — high
    "S09": 0.70,   # whale dominance     — high
    "S10": 0.75,   # sybil clusters      — high
    "S11": 0.90,   # rug history         — critical
    "S12": 0.80,   # wallet age          — critical
    "S13": 0.65,   # suspicious tx       — high
    "S14": 0.60,   # bot spike           — high
    "S15": 0.65,   # wash trading        — high
    "S16": 0.85,   # insider dump        — critical
    "S17": 0.55,   # social verify       — medium
    "S18": 0.50,   # fake engagement     — medium
}


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_model():
    if not MODEL_PATH.exists():
        print("[ERROR] Model not found. Run python3 train_model.py first.")
        sys.exit(1)
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _risk_label(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 30:
        return "MEDIUM"
    else:
        return "LOW"


def _recommendation(score: int) -> str:
    if score >= 80:
        return "DO NOT BUY. Extremely high probability of rug pull."
    elif score >= 60:
        return "HIGH RISK. Avoid unless you can verify all red flags manually."
    elif score >= 30:
        return "MEDIUM RISK. Proceed with caution and small position sizes."
    else:
        return "LOW RISK. Token appears safe based on available signals."


# ------------------------------------------------------------------ #
#  Run all 18 signals                                                 #
# ------------------------------------------------------------------ #

def run_all_signals(token_address: str) -> list[dict]:
    from signals.signals import run_all_signals as run_base
    from signals.graph_signals import run_graph_signals
    from signals.behavioral_signals import run_behavioral_signals

    results = []
    results += run_base(token_address)
    results += run_graph_signals(token_address, deployer_wallet=token_address)
    results += run_behavioral_signals(token_address)
    return results


# ------------------------------------------------------------------ #
#  Compute final 0–100 score                                          #
# ------------------------------------------------------------------ #

def compute_score(signals: list[dict], ml_model) -> dict:
    """
    Combines:
      - Weighted average of rule-based signal scores (60% weight)
      - ML model probability of being a scam (40% weight)
    Returns a 0–100 integer risk score.
    """
    # Rule-based weighted average
    total_weight = 0
    weighted_sum = 0
    signal_map   = {}

    for sig in signals:
        sid    = sig["signal_id"]
        score  = sig["score"]
        weight = SIGNAL_WEIGHTS.get(sid, 0.5)
        weighted_sum += score * weight
        total_weight += weight
        signal_map[sid] = score

    rule_score = weighted_sum / total_weight if total_weight > 0 else 0.5

    # ML probability
    feature_order = [
        "S01", "S02", "S03", "S04", "S05", "S06",
        "S07",  # placeholder — always 0
        "S08", "S09", "S10", "S11", "S12", "S13",
        "S14", "S15", "S16", "S17", "S18",
    ]
    features = [[signal_map.get(sid, 0.0) for sid in feature_order]]

    try:
        ml_prob = ml_model.predict_proba(features)[0][1]  # probability of scam
    except Exception:
        ml_prob = rule_score  # fallback if model fails

    # Blend: 60% rule-based + 40% ML
    combined = (0.60 * rule_score) + (0.40 * ml_prob)

    # Convert to 0–100 integer
    final_score = round(combined * 100)

    return {
        "final_score":   final_score,
        "rule_score":    round(rule_score * 100, 1),
        "ml_score":      round(ml_prob * 100, 1),
        "signal_scores": {sid: round(score * 100, 1)
                          for sid, score in signal_map.items()},
    }


# ------------------------------------------------------------------ #
#  Main output builder                                                #
# ------------------------------------------------------------------ #

def score_token(token_address: str) -> dict:
    print(f"\nScoring token: {token_address}")
    print("Running 18 signals...")

    model   = _load_model()
    signals = run_all_signals(token_address)
    scores  = compute_score(signals, model)

    final   = scores["final_score"]
    risk    = _risk_label(final)

    output = {
        "token_address":    token_address,
        "risk_score":       final,           # 0–100
        "risk_level":       risk,            # LOW | MEDIUM | HIGH | CRITICAL
        "recommendation":   _recommendation(final),
        "scoring_breakdown": {
            "rule_based_score": scores["rule_score"],
            "ml_model_score":   scores["ml_score"],
            "final_score":      final,
            "blend":            "60% rule-based + 40% ML model",
        },
        "signals": [
            {
                "signal_id":  s["signal_id"],
                "score":      s["score"],
                "risk_level": s["risk_level"],
                "check":      s["details"]["check"],
                "explanation":s["details"]["explanation"],
            }
            for s in signals
        ],
        "timestamp": _now(),
    }

    return output


# ------------------------------------------------------------------ #
#  Entry point                                                        #
# ------------------------------------------------------------------ #

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scorer.py <token_address>")
        print("Example:")
        print("  python3 scorer.py So11111111111111111111111111111111111111112")
        sys.exit(1)

    token_address = sys.argv[1]
    result = score_token(token_address)

    # Pretty print
    print("\n" + "="*60)
    print(f"  RISK SCORE : {result['risk_score']} / 100")
    print(f"  RISK LEVEL : {result['risk_level']}")
    print(f"  VERDICT    : {result['recommendation']}")
    print("="*60)
    print(f"\n  Rule-based score : {result['scoring_breakdown']['rule_based_score']}")
    print(f"  ML model score   : {result['scoring_breakdown']['ml_model_score']}")
    print(f"\n  Signal breakdown:")
    for sig in result["signals"]:
        bar = "█" * int(sig["score"] * 20)
        print(f"    {sig['signal_id']}  {sig['score']:.2f}  {bar}")

    # Save JSON output
    out_path = BASE / "output" / f"{token_address[:8]}_score.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Full JSON saved → {out_path}")


if __name__ == "__main__":
    main()
