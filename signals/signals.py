"""
Signal implementations S01–S09 (S07 skipped per spec).

Each signal function returns a dict matching contracts.md format exactly:
{
    "signal_id":  str,
    "token_address": str,
    "score":      float,          # 0.0 – 1.0
    "risk_level": str,            # LOW | MEDIUM | HIGH | CRITICAL
    "details": {
        "check":       str,
        "result":      any,
        "explanation": str,
    },
    "timestamp":  str             # ISO 8601 UTC
}
"""

from datetime import datetime, timezone
from config import score_to_risk
from solana_rpc import get_account_info, get_lp_info, get_holder_info


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(signal_id, token_address, score, check, result, explanation) -> dict:
    return {
        "signal_id":     signal_id,
        "token_address": token_address,
        "score":         round(score, 4),
        "risk_level":    score_to_risk(score),
        "details": {
            "check":       check,
            "result":      result,
            "explanation": explanation,
        },
        "timestamp": _now(),
    }


# --------------------------------------------------------------------------- #
#  S01 — Mint Authority Check                                                  #
# --------------------------------------------------------------------------- #

def signal_01_mint_authority(token_address: str) -> dict:
    """
    HIGH risk if mint authority is still enabled — creator can print tokens
    at will, diluting all holders.
    Score: 0.9 if authority present, 0.0 if revoked/null.
    """
    info = get_account_info(token_address)
    authority = info.get("mint_authority")
    has_authority = authority is not None

    score = 0.9 if has_authority else 0.0
    explanation = (
        f"Mint authority is ACTIVE ({authority}). "
        "Creator can mint unlimited tokens — severe rug risk."
        if has_authority else
        "Mint authority has been revoked. Supply is fixed — low risk."
    )

    return _build(
        "S01", token_address, score,
        check="mint_authority_present",
        result=authority,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S02 — Freeze Authority Check                                                #
# --------------------------------------------------------------------------- #

def signal_02_freeze_authority(token_address: str) -> dict:
    """
    MEDIUM risk if freeze authority is still set — creator can freeze
    holder wallets, preventing sells.
    Score: 0.7 if present, 0.0 if revoked.
    """
    info = get_account_info(token_address)
    authority = info.get("freeze_authority")
    has_authority = authority is not None

    score = 0.7 if has_authority else 0.0
    explanation = (
        f"Freeze authority is ACTIVE ({authority}). "
        "Creator can freeze token accounts — holders may be locked out."
        if has_authority else
        "Freeze authority has been revoked. Accounts cannot be frozen."
    )

    return _build(
        "S02", token_address, score,
        check="freeze_authority_present",
        result=authority,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S03 — Upgradeable Contract Check                                            #
# --------------------------------------------------------------------------- #

def signal_03_upgradeable_contract(token_address: str) -> dict:
    """
    HIGH risk if the program is upgradeable — logic can be swapped post-deploy.
    Score: 0.75 if upgradeable, 0.05 if immutable.
    """
    info = get_account_info(token_address)
    upgradeable = info.get("upgradeable", False)

    score = 0.75 if upgradeable else 0.05
    explanation = (
        "Program is UPGRADEABLE. The upgrade authority can replace contract "
        "logic at any time — behaviour can change without warning."
        if upgradeable else
        "Program is immutable. Contract logic cannot be changed."
    )

    return _build(
        "S03", token_address, score,
        check="program_upgradeable",
        result=upgradeable,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S04 — Metadata Mutability Check                                             #
# --------------------------------------------------------------------------- #

def signal_04_metadata_mutability(token_address: str) -> dict:
    """
    MEDIUM risk if on-chain metadata (name, symbol, URI) is still mutable —
    could be swapped for a scam after gaining trust.
    Score: 0.55 if mutable, 0.0 if immutable.
    """
    info = get_account_info(token_address)
    mutable = info.get("mutable_metadata", True)

    score = 0.55 if mutable else 0.0
    explanation = (
        "Token metadata is MUTABLE. Name, symbol, or image URI can be "
        "changed post-launch — identity switching risk."
        if mutable else
        "Token metadata is IMMUTABLE. Identity cannot be altered."
    )

    return _build(
        "S04", token_address, score,
        check="metadata_mutable",
        result=mutable,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S05 — LP Lock Status Check                                                  #
# --------------------------------------------------------------------------- #

def signal_05_lp_lock_status(token_address: str) -> dict:
    """
    Risk inversely proportional to LP lock percentage.
    Score: 1.0 - locked_pct  (fully locked → 0.0, fully unlocked → 1.0)
    """
    lp = get_lp_info(token_address)
    locked_pct = lp.get("lp_locked_percent", 0.0)

    score = round(1.0 - locked_pct, 4)
    explanation = (
        f"{locked_pct * 100:.1f}% of LP tokens are locked. "
        + (
            "Very low lock — liquidity can be pulled at any time (rug risk)."
            if score > 0.6 else
            "Moderate lock — partial protection against liquidity pulls."
            if score > 0.3 else
            "High lock — strong protection against LP rug pulls."
        )
    )

    return _build(
        "S05", token_address, score,
        check="lp_locked_percent",
        result=locked_pct,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S06 — Deployer LP Concentration Check                                       #
# --------------------------------------------------------------------------- #

def signal_06_deployer_lp_concentration(token_address: str) -> dict:
    """
    Risk scales with the fraction of LP tokens held by the deployer.
    Score = deployer_lp_percent (0 → 0.0, 1 → 1.0).
    """
    lp = get_lp_info(token_address)
    deployer_pct = lp.get("deployer_lp_percent", 0.0)

    score = round(min(deployer_pct, 1.0), 4)
    explanation = (
        f"Deployer controls {deployer_pct * 100:.1f}% of LP tokens. "
        + (
            "Deployer holds majority of LP — can drain liquidity instantly."
            if score >= 0.5 else
            "Deployer holds significant LP — elevated rug risk."
            if score >= 0.25 else
            "Deployer LP concentration is low — reduced rug risk."
        )
    )

    return _build(
        "S06", token_address, score,
        check="deployer_lp_percent",
        result=deployer_pct,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S08 — Top 10 Holder Concentration                                           #
# --------------------------------------------------------------------------- #

def signal_08_top10_concentration(token_address: str) -> dict:
    """
    Risk scales with the combined supply percentage held by top 10 wallets.
    Score = top_10_concentration (capped at 1.0).
    """
    holders = get_holder_info(token_address)
    concentration = holders.get("top_10_concentration", 0.0)

    score = round(min(concentration, 1.0), 4)
    explanation = (
        f"Top 10 wallets hold {concentration * 100:.1f}% of supply. "
        + (
            "Extreme concentration — coordinated dump could crater price."
            if score >= 0.8 else
            "High concentration — significant sell pressure risk."
            if score >= 0.5 else
            "Moderate concentration — typical for early-stage tokens."
            if score >= 0.3 else
            "Well distributed supply — low dump risk from top holders."
        )
    )

    return _build(
        "S08", token_address, score,
        check="top_10_holder_concentration",
        result={
            "top_10_concentration": concentration,
            "holders": holders.get("holders", []),
        },
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  S09 — Whale Dominance Check                                                 #
# --------------------------------------------------------------------------- #

def signal_09_whale_dominance(token_address: str) -> dict:
    """
    Focuses on the single largest holder.
    Score scales sharply: >30 % → CRITICAL, 10–30 % → HIGH, <10 % → LOW.
    """
    holders = get_holder_info(token_address)
    top_pct = holders.get("top_holder_percent", 0.0)

    if top_pct >= 0.5:
        score = 0.95
    elif top_pct >= 0.3:
        score = 0.85
    elif top_pct >= 0.1:
        score = 0.65
    elif top_pct >= 0.05:
        score = 0.4
    else:
        score = 0.1

    explanation = (
        f"Largest single holder owns {top_pct * 100:.1f}% of supply. "
        + (
            "Single whale dominance — one wallet can collapse the token."
            if score >= 0.8 else
            "Significant whale — large coordinated sell risk."
            if score >= 0.6 else
            "Moderate whale presence — manageable but watch closely."
            if score >= 0.35 else
            "No single whale dominance — healthy distribution."
        )
    )

    return _build(
        "S09", token_address, score,
        check="top_holder_percent",
        result=top_pct,
        explanation=explanation,
    )


# --------------------------------------------------------------------------- #
#  Convenience: run all signals                                                #
# --------------------------------------------------------------------------- #

ALL_SIGNALS = [
    signal_01_mint_authority,
    signal_02_freeze_authority,
    signal_03_upgradeable_contract,
    signal_04_metadata_mutability,
    signal_05_lp_lock_status,
    signal_06_deployer_lp_concentration,
    signal_08_top10_concentration,
    signal_09_whale_dominance,
]


def run_all_signals(token_address: str) -> list[dict]:
    return [fn(token_address) for fn in ALL_SIGNALS]
