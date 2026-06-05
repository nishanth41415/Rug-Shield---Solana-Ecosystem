"""
signals/graph_signals.py — S10 through S13 (P1 graph analyzer signals).
"""

import importlib.util
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import score_to_risk
from signals.utils import NEUTRAL_SCORE, mark_non_evidence, set_data_source

_graph_cache: dict[str, dict] = {}
_calculate_graph_risk_fn = None


def _load_calculate_graph_risk():
    """Load calculate_graph_risk without package/dir name clash."""
    global _calculate_graph_risk_fn
    if _calculate_graph_risk_fn is not None:
        return _calculate_graph_risk_fn
    ga_path = Path(__file__).parent.parent / "graph_analyzer" / "graph_analyzer.py"
    spec = importlib.util.spec_from_file_location("ga_impl", ga_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _calculate_graph_risk_fn = mod.calculate_graph_risk
    return _calculate_graph_risk_fn


def _get_graph_data(deployer_wallet: str) -> dict:
    if deployer_wallet in _graph_cache:
        return _graph_cache[deployer_wallet]

    default = {
        "deployerWallet":  deployer_wallet,
        "walletAgeDays":   0,
        "deployerFlagged": False,
        "sybilClusters":   0,
        "hopDistance":     0,
        "_meta": {
            "wallet_age_source": "unavailable",
            "rug_db_source":     "unavailable",
            "graph_source":      "unavailable",
        },
    }

    try:
        fn = _load_calculate_graph_risk()
        result = fn(deployer_wallet)
        _graph_cache[deployer_wallet] = result
        return result
    except Exception as e:
        print(f"  [WARN] graph_analyzer unavailable ({e}) — graph signals unavailable")
        _graph_cache[deployer_wallet] = default
        return default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(signal_id: str, token_address: str, score: float,
           check: str, result, explanation: str) -> dict:
    score = round(float(score), 4)
    return {
        "signal_id":     signal_id,
        "token_address": token_address,
        "score":         score,
        "risk_level":    score_to_risk(score),
        "details": {
            "check":       check,
            "result":      result,
            "explanation": explanation,
        },
        "timestamp": _now(),
    }


def _meta(data: dict) -> dict:
    return data.get("_meta", {})


def signal_10_sybil_clustering(token_address: str, deployer_wallet: str) -> dict:
    data = _get_graph_data(deployer_wallet)
    meta = _meta(data)

    if meta.get("graph_source") != "real":
        return mark_non_evidence(_build(
            "S10", token_address, NEUTRAL_SCORE,
            check="sybil_clusters",
            result={"sybil_clusters": None},
            explanation="Wallet graph data unavailable — sybil cluster check skipped.",
        ), "unavailable")

    clusters = data.get("sybilClusters", 0)
    score_map = {0: 0.00, 1: 0.40, 2: 0.65, 3: 0.80}
    score = score_map.get(clusters, 0.95)

    explanation = (
        f"{clusters} sybil cluster(s) detected around deployer wallet. "
        + (
            "No sybil activity — wallets appear independent."
            if clusters == 0 else
            "Multiple linked wallet clusters detected — likely coordinated fake activity."
            if clusters >= 2 else
            "One sybil cluster detected — possible fake wallet coordination."
        )
    )

    return set_data_source(_build(
        "S10", token_address, score,
        check="sybil_clusters",
        result={"deployer_wallet": deployer_wallet[:8] + "...",
                "sybil_clusters": clusters},
        explanation=explanation,
    ), "real")


def signal_11_rug_history(token_address: str, deployer_wallet: str) -> dict:
    data = _get_graph_data(deployer_wallet)
    meta = _meta(data)
    flagged = data.get("deployerFlagged", False)
    hop = data.get("hopDistance", 0)

    if meta.get("rug_db_source") != "real" and meta.get("graph_source") != "real":
        return mark_non_evidence(_build(
            "S11", token_address, NEUTRAL_SCORE,
            check="rug_pull_history",
            result={"deployer_flagged": None, "hop_distance": None},
            explanation="Rug history database unavailable — check skipped.",
        ), "unavailable")

    if flagged:
        score = 0.95
        explanation = (
            f"Deployer wallet ({deployer_wallet[:8]}...) is in the confirmed rug pull "
            "database. This wallet has rugged before — DO NOT BUY."
        )
        result = {"deployer_flagged": True, "hop_distance": 0}
        src = "real"
    elif hop > 0 and meta.get("graph_source") == "real":
        score = max(0.75 - (hop - 1) * 0.20, 0.35)
        explanation = (
            f"Deployer is {hop} hop(s) away from a known rugger in the wallet graph. "
            "Indirect association with confirmed bad actors."
        )
        result = {"deployer_flagged": False, "hop_distance": hop}
        src = "real"
    elif meta.get("rug_db_source") == "real":
        score = 0.05
        explanation = (
            "Deployer wallet has no rug pull history and is not connected "
            "to any known ruggers in the wallet graph."
        )
        result = {"deployer_flagged": False, "hop_distance": 0}
        src = "real"
    else:
        return mark_non_evidence(_build(
            "S11", token_address, NEUTRAL_SCORE,
            check="rug_pull_history",
            result={"deployer_flagged": False, "hop_distance": 0},
            explanation="Partial rug-history data only — no evidence available.",
        ), "unavailable")

    return set_data_source(_build(
        "S11", token_address, score,
        check="rug_pull_history",
        result=result,
        explanation=explanation,
    ), src)


def signal_12_wallet_age(token_address: str, deployer_wallet: str) -> dict:
    data = _get_graph_data(deployer_wallet)
    meta = _meta(data)
    age_days = data.get("walletAgeDays", 0)

    if meta.get("wallet_age_source") != "real":
        return mark_non_evidence(_build(
            "S12", token_address, NEUTRAL_SCORE,
            check="wallet_age_days",
            result={"wallet_age_days": None},
            explanation="Deployer wallet age unavailable — cannot assess wallet maturity.",
        ), "unavailable")

    if age_days < 7:
        score = 0.95
        label = "brand new (< 7 days)"
    elif age_days < 30:
        score = 0.75
        label = "very new (< 30 days)"
    elif age_days < 90:
        score = 0.40
        label = "relatively new (< 90 days)"
    else:
        score = 0.05
        label = "established (90+ days)"

    explanation = (
        f"Deployer wallet is {age_days} day(s) old — {label}. "
        + (
            "Extremely new wallets are almost always disposable rug accounts."
            if age_days < 7 else
            "Wallets under 30 days are a strong rug pull indicator."
            if age_days < 30 else
            "Relatively new wallet — not an immediate red flag alone."
            if age_days < 90 else
            "Established wallet with a real history — lower risk."
        )
    )

    return set_data_source(_build(
        "S12", token_address, score,
        check="wallet_age_days",
        result={"deployer_wallet": deployer_wallet[:8] + "...",
                "wallet_age_days": age_days},
        explanation=explanation,
    ), "real")


def signal_13_suspicious_tx_patterns(token_address: str, deployer_wallet: str) -> dict:
    data = _get_graph_data(deployer_wallet)
    meta = _meta(data)

    if meta.get("graph_source") != "real":
        return mark_non_evidence(_build(
            "S13", token_address, NEUTRAL_SCORE,
            check="suspicious_tx_patterns",
            result={"sybil_clusters": None, "hop_distance": None},
            explanation="Transaction pattern graph unavailable — check skipped.",
        ), "unavailable")

    clusters = data.get("sybilClusters", 0)
    hop = data.get("hopDistance", 0)

    sybil_score = min(clusters * 0.20, 0.80)
    proximity_map = {0: 0.00, 1: 0.80, 2: 0.50}
    proximity_score = proximity_map.get(hop, 0.30)
    score = round(0.5 * sybil_score + 0.5 * proximity_score, 4)

    flags = []
    if clusters > 0:
        flags.append(f"{clusters} sybil cluster(s) suggesting circular fund flows")
    if hop > 0:
        flags.append(f"wallet graph links to known rugger in {hop} hop(s)")
    if not flags:
        flags.append("no suspicious patterns detected")

    explanation = f"Suspicious transaction pattern analysis: {'; '.join(flags)}."

    return set_data_source(_build(
        "S13", token_address, score,
        check="suspicious_tx_patterns",
        result={
            "sybil_clusters":  clusters,
            "hop_distance":    hop,
            "sybil_score":     round(sybil_score, 4),
            "proximity_score": round(proximity_score, 4),
        },
        explanation=explanation,
    ), "real")


GRAPH_SIGNALS = [
    signal_10_sybil_clustering,
    signal_11_rug_history,
    signal_12_wallet_age,
    signal_13_suspicious_tx_patterns,
]


def run_graph_signals(token_address: str, deployer_wallet: str) -> list[dict]:
    results = []
    for fn in GRAPH_SIGNALS:
        try:
            results.append(fn(token_address, deployer_wallet))
        except Exception as e:
            print(f"  [WARN] {fn.__name__} raised an unexpected error: {e}")
    return results
