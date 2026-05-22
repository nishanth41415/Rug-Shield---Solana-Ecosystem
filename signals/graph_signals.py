"""
graph_signals.py — Signals S10–S13 built on top of P1's graph_analyzer output.

P1's calculate_graph_risk() returns this dict:
{
    "deployerWallet":  str,   # wallet address
    "walletAgeDays":   int,   # how old the wallet is in days
    "deployerFlagged": bool,  # True if wallet is in the confirmed rug DB
    "sybilClusters":   int,   # number of sybil clusters detected
    "hopDistance":     int,   # hops to nearest known rugger (0 = not found)
}

We import calculate_graph_risk and pass the deployer wallet address.
If P1's code or the DB is unavailable we fall back to a deterministic mock
so the rest of the pipeline never crashes.
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import score_to_risk


# ------------------------------------------------------------------ #
#  P1 integration — safe import with mock fallback                    #
# ------------------------------------------------------------------ #

def _get_graph_data(deployer_wallet: str) -> dict:
    """
    Try to call P1's calculate_graph_risk().
    Falls back to deterministic mock if P1's code / DB is not reachable.
    """
    try:
        # P1's file must be in graph_analyzer/ inside the project root
        sys.path.insert(0, str(Path(__file__).parent.parent / "graph_analyzer"))
        from graph_analyzer import calculate_graph_risk
        return calculate_graph_risk(deployer_wallet)
    except Exception:
        return _mock_graph_data(deployer_wallet)


def _mock_graph_data(deployer_wallet: str) -> dict:
    """Deterministic mock derived from the wallet address hash."""
    seed = int(hashlib.sha256(deployer_wallet.encode()).hexdigest(), 16)
    return {
        "deployerWallet":  deployer_wallet,
        "walletAgeDays":   seed % 120,          # 0–119 days
        "deployerFlagged": bool(seed % 7 == 0), # ~14 % flagged
        "sybilClusters":   seed % 5,            # 0–4 clusters
        "hopDistance":     seed % 4,            # 0–3 hops (0 = none found)
    }


# ------------------------------------------------------------------ #
#  Shared builder                                                     #
# ------------------------------------------------------------------ #

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(signal_id, token_address, score, check, result, explanation) -> dict:
    return {
        "signal_id":     signal_id,
        "token_address": token_address,
        "score":         round(float(score), 4),
        "risk_level":    score_to_risk(score),
        "details": {
            "check":       check,
            "result":      result,
            "explanation": explanation,
        },
        "timestamp": _now(),
    }


# ------------------------------------------------------------------ #
#  S10 — Sybil Wallet Clustering                                      #
# ------------------------------------------------------------------ #

def signal_10_sybil_clustering(token_address: str, deployer_wallet: str) -> dict:
    """
    Uses P1 field: sybilClusters (int)
    More clusters = higher risk that deployer controls many fake wallets
    to simulate organic activity.

    Score:
        0 clusters  → 0.0  (no sybil activity)
        1 cluster   → 0.4
        2 clusters  → 0.65
        3 clusters  → 0.8
        4+ clusters → 0.95
    """
    data = _get_graph_data(deployer_wallet)
    clusters = data.get("sybilClusters", 0)

    score_map = {0: 0.0, 1: 0.4, 2: 0.65, 3: 0.8}
    score = score_map.get(clusters, 0.95)  # 4+ → 0.95

    explanation = (
        f"{clusters} sybil cluster(s) detected around deployer wallet. "
        + (
            "No sybil activity — wallets appear independent."
            if clusters == 0 else
            "Multiple linked wallets detected — likely coordinated fake activity."
            if clusters >= 2 else
            "One sybil cluster detected — possible fake wallet coordination."
        )
    )

    return _build(
        "S10", token_address, score,
        check="sybil_clusters",
        result={"deployer_wallet": deployer_wallet, "sybil_clusters": clusters},
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S11 — Previous Rug Pull History                                    #
# ------------------------------------------------------------------ #

def signal_11_rug_history(token_address: str, deployer_wallet: str) -> dict:
    """
    Uses P1 fields: deployerFlagged (bool) + hopDistance (int)

    If deployerFlagged=True  → deployer is a confirmed rugger → CRITICAL (0.95)
    If hopDistance > 0       → connected to a known rugger within N hops
        hop 1 → 0.75  (direct connection)
        hop 2 → 0.55
        hop 3 → 0.35
    No connection            → 0.05
    """
    data = _get_graph_data(deployer_wallet)
    flagged = data.get("deployerFlagged", False)
    hop = data.get("hopDistance", 0)

    if flagged:
        score = 0.95
        explanation = (
            f"Deployer wallet ({deployer_wallet[:8]}...) is in the confirmed rug pull "
            "database. This wallet has rugged before."
        )
        result = {"deployer_flagged": True, "hop_distance": 0}
    elif hop > 0:
        score = max(0.75 - (hop - 1) * 0.2, 0.35)
        explanation = (
            f"Deployer is {hop} hop(s) away from a known rugger in the wallet graph. "
            "Indirect association with confirmed bad actors."
        )
        result = {"deployer_flagged": False, "hop_distance": hop}
    else:
        score = 0.05
        explanation = (
            "Deployer wallet has no history of rug pulls and is not connected "
            "to any known ruggers in the graph."
        )
        result = {"deployer_flagged": False, "hop_distance": 0}

    return _build(
        "S11", token_address, score,
        check="rug_pull_history",
        result=result,
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S12 — Wallet Age Under 30 Days                                     #
# ------------------------------------------------------------------ #

def signal_12_wallet_age(token_address: str, deployer_wallet: str) -> dict:
    """
    Uses P1 field: walletAgeDays (int)

    New wallets are created specifically for rug pulls to avoid history.
    Score:
        < 7 days  → 0.95 (brand new — almost certainly disposable)
        < 30 days → 0.75 (suspicious)
        < 90 days → 0.4  (relatively new)
        90+ days  → 0.05 (established wallet)
    """
    data = _get_graph_data(deployer_wallet)
    age_days = data.get("walletAgeDays", 0)

    if age_days < 7:
        score = 0.95
        label = "brand new (< 7 days)"
    elif age_days < 30:
        score = 0.75
        label = "very new (< 30 days)"
    elif age_days < 90:
        score = 0.4
        label = "relatively new (< 90 days)"
    else:
        score = 0.05
        label = "established (90+ days)"

    explanation = (
        f"Deployer wallet is {age_days} day(s) old — {label}. "
        + (
            "Extremely new wallets are almost always disposable rug accounts."
            if age_days < 7 else
            "Wallets under 30 days old are a strong rug pull indicator."
            if age_days < 30 else
            "Wallet is relatively new but not an immediate red flag."
            if age_days < 90 else
            "Wallet has an established history — lower risk."
        )
    )

    return _build(
        "S12", token_address, score,
        check="wallet_age_days",
        result={"deployer_wallet": deployer_wallet, "wallet_age_days": age_days},
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S13 — Suspicious Transaction Patterns                              #
# ------------------------------------------------------------------ #

def signal_13_suspicious_tx_patterns(token_address: str, deployer_wallet: str) -> dict:
    """
    Uses P1 fields: sybilClusters + hopDistance combined.
    Detects circular fund flows and layering by looking at how many
    cluster connections exist AND how close a known bad actor is.

    Score = weighted combo:
        0.5 × sybil_score  +  0.5 × proximity_score
    """
    data = _get_graph_data(deployer_wallet)
    clusters = data.get("sybilClusters", 0)
    hop = data.get("hopDistance", 0)

    # Sybil component
    sybil_score = min(clusters * 0.2, 0.8)

    # Proximity component — closer to a rugger = more suspicious tx patterns
    if hop == 0:
        proximity_score = 0.0
    elif hop == 1:
        proximity_score = 0.8
    elif hop == 2:
        proximity_score = 0.5
    else:
        proximity_score = 0.3

    score = round(0.5 * sybil_score + 0.5 * proximity_score, 4)

    flags = []
    if clusters > 0:
        flags.append(f"{clusters} sybil cluster(s) suggest circular fund flows")
    if hop > 0:
        flags.append(f"wallet graph connects to known rugger in {hop} hop(s)")
    if not flags:
        flags.append("no suspicious patterns detected")

    explanation = (
        f"Suspicious transaction pattern analysis: {'; '.join(flags)}."
    )

    return _build(
        "S13", token_address, score,
        check="suspicious_tx_patterns",
        result={
            "sybil_clusters":   clusters,
            "hop_distance":     hop,
            "sybil_score":      round(sybil_score, 4),
            "proximity_score":  round(proximity_score, 4),
        },
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  Convenience: run all graph signals                                 #
# ------------------------------------------------------------------ #

GRAPH_SIGNALS = [
    signal_10_sybil_clustering,
    signal_11_rug_history,
    signal_12_wallet_age,
    signal_13_suspicious_tx_patterns,
]


def run_graph_signals(token_address: str, deployer_wallet: str) -> list[dict]:
    """Run S10–S13 for a given token and its deployer wallet."""
    return [fn(token_address, deployer_wallet) for fn in GRAPH_SIGNALS]
