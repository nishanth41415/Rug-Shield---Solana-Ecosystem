"""
signals/signals.py — S01 through S09 (on-chain authority + holder signals).

All signals use REAL Solana mainnet RPC data.
Every signal falls back to a deterministic mock if the RPC call fails,
so scoring NEVER crashes even on network errors.

Signals implemented:
    S01 — Mint authority active
    S02 — Freeze authority active
    S03 — Upgradeable program contract
    S04 — Mutable token metadata (Metaplex)
    S05 — LP lock status
    S06 — Deployer LP concentration
    S07 — SKIPPED (placeholder = 0 per project spec)
    S08 — Top-10 holder concentration
    S09 — Whale dominance (largest single holder)
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Allow running this file directly from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import score_to_risk
from signals.utils import set_data_source
from solana_rpc import (
    get_account_info,
    get_metadata_account,
    get_program_upgrade_authority,
    get_holder_info,
    get_lp_info,
)

# ---------------------------------------------------------------------------
#  Shared builder
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
#  S01 — Mint Authority Check
# ---------------------------------------------------------------------------

def signal_01_mint_authority(token_address: str) -> dict:
    """
    CRITICAL risk if mint authority is still active.
    An active mint authority can print unlimited tokens, instantly diluting holders.

    Score: 0.9 if active, 0.0 if revoked.
    Data: Real — getAccountInfo (jsonParsed) → mintAuthority field.
    """
    info      = get_account_info(token_address)
    authority = info.get("mint_authority")
    has_auth  = authority is not None

    score = 0.9 if has_auth else 0.0
    explanation = (
        f"Mint authority is ACTIVE ({authority}). "
        "Creator can mint unlimited new tokens, diluting all holders."
        if has_auth else
        "Mint authority has been revoked. No new tokens can ever be minted."
    )

    return set_data_source(_build(
        "S01", token_address, score,
        check="mint_authority_present",
        result=authority,
        explanation=explanation,
    ), info.get("source", "real"))


# ---------------------------------------------------------------------------
#  S02 — Freeze Authority Check
# ---------------------------------------------------------------------------

def signal_02_freeze_authority(token_address: str) -> dict:
    """
    HIGH risk if freeze authority is still active.
    Deployer can freeze any holder's token account, locking their funds.

    Score: 0.7 if active, 0.0 if revoked.
    Data: Real — getAccountInfo (jsonParsed) → freezeAuthority field.
    """
    info      = get_account_info(token_address)
    authority = info.get("freeze_authority")
    has_auth  = authority is not None

    score = 0.7 if has_auth else 0.0
    explanation = (
        f"Freeze authority is ACTIVE ({authority}). "
        "Creator can freeze any holder's token account — holders may be locked out."
        if has_auth else
        "Freeze authority has been revoked. Token accounts cannot be frozen."
    )

    return set_data_source(_build(
        "S02", token_address, score,
        check="freeze_authority_present",
        result=authority,
        explanation=explanation,
    ), info.get("source", "real"))


# ---------------------------------------------------------------------------
#  S03 — Upgradeable Program Contract
# ---------------------------------------------------------------------------

def signal_03_upgradeable_contract(token_address: str) -> dict:
    """
    HIGH risk if the token's associated program is upgradeable.
    An upgrade authority means contract logic can be silently replaced.

    Score: 0.75 if upgradeable, 0.05 if immutable.
    Data: Real — getAccountInfo on the program account, checks BPF loader type.

    Note: Most SPL Token mints use the standard SPL Token program (immutable).
    Custom programs (e.g. meme coins with custom logic) are where this matters.
    We check the mint account's owner program for the upgrade authority.
    """
    # Get the owner program of the mint account
    result = None
    try:
        from solana_rpc import _rpc
        raw = _rpc(
            "getAccountInfo",
            [token_address, {"encoding": "jsonParsed", "commitment": "confirmed"}],
        )
        if raw and raw.get("value"):
            owner_program = raw["value"].get("owner", "")
            result        = get_program_upgrade_authority(owner_program)
    except Exception:
        pass

    if result is None:
        result = get_program_upgrade_authority(token_address)

    upgradeable = result.get("upgradeable", False)
    authority   = result.get("upgrade_authority")

    score = 0.75 if upgradeable else 0.05
    explanation = (
        f"Program is UPGRADEABLE (authority: {authority}). "
        "Contract logic can be replaced at any time without holder consent."
        if upgradeable else
        "Program is immutable. Contract logic is locked and cannot be changed."
    )

    return set_data_source(_build(
        "S03", token_address, score,
        check="program_upgradeable",
        result={"upgradeable": upgradeable, "upgrade_authority": authority},
        explanation=explanation,
    ), result.get("source", "real"))


# ---------------------------------------------------------------------------
#  S04 — Metadata Mutability Check
# ---------------------------------------------------------------------------

def signal_04_metadata_mutability(token_address: str) -> dict:
    """
    MEDIUM risk if on-chain Metaplex metadata is still mutable.
    Mutable metadata lets the deployer swap the token's name, symbol, or image
    URI after launch — a classic identity-bait-and-switch tactic.

    Score: 0.55 if mutable, 0.0 if immutable.
    Data: Real — Metaplex metadata PDA → isMutable byte.
    """
    meta   = get_metadata_account(token_address)
    mutable = meta.get("is_mutable", True)

    score = 0.55 if mutable else 0.0
    explanation = (
        "Token metadata is MUTABLE. The deployer can change name, symbol, or image "
        "URI post-launch — identity bait-and-switch risk."
        if mutable else
        "Token metadata is IMMUTABLE. Name, symbol, and image cannot be altered."
    )

    return set_data_source(_build(
        "S04", token_address, score,
        check="metadata_mutable",
        result=mutable,
        explanation=explanation,
    ), meta.get("source", "real"))


# ---------------------------------------------------------------------------
#  S05 — LP Lock Status
# ---------------------------------------------------------------------------

def signal_05_lp_lock_status(token_address: str) -> dict:
    """
    Risk is inversely proportional to LP lock percentage.
    Unlocked LP = deployer can drain the pool instantly (classic rug pull).

    Score: 1.0 − locked_pct  (fully locked → 0.0, fully unlocked → 1.0)
    Data: Real — DexScreener public API (no key needed).
    """
    lp         = get_lp_info(token_address)
    locked_pct = lp.get("lp_locked_percent", 0.0)
    liquidity  = lp.get("liquidity_usd", 0.0)
    raw_source = lp.get("source", "mock")
    source     = "real" if raw_source == "dexscreener" else raw_source
    dex        = lp.get("dex", "unknown")

    score = round(1.0 - locked_pct, 4)

    if liquidity == 0.0:
        if source == "mock":
            score = 0.5
            source = "unavailable"
            explanation = (
                "Liquidity pool data unavailable — LP lock cannot be assessed."
            )
        else:
            explanation = (
                "No liquidity pool found on DexScreener for this token. "
                "Either not listed yet or pool has been drained — treat as maximum rug risk."
            )
            score = 1.0
    else:
        explanation = (
            f"{locked_pct * 100:.1f}% of LP tokens are locked "
            f"(pool: {dex}, liquidity: ${liquidity:,.0f}). "
            + (
                "Very low lock — liquidity can be pulled at any time (rug risk)."
                if score > 0.6 else
                "Moderate lock — partial protection against liquidity pulls."
                if score > 0.3 else
                "High lock — strong protection against LP rug pulls."
            )
        )

    out = _build(
        "S05", token_address, score,
        check="lp_locked_percent",
        result=locked_pct,
        explanation=explanation,
    )
    out["details"]["liquidity_usd"] = liquidity
    out["details"]["dex"] = dex
    out["details"]["data_source"] = source
    return out


# ---------------------------------------------------------------------------
#  S06 — Deployer LP Concentration
# ---------------------------------------------------------------------------

def signal_06_deployer_lp_concentration(token_address: str) -> dict:
    """
    Risk scales with the fraction of LP tokens controlled by the deployer.
    High deployer LP = can pull liquidity unilaterally.

    Score: deployer_lp_percent (0 → 0.0, 1 → 1.0).
    Data: Real — DexScreener public API (no key needed).
    """
    lp           = get_lp_info(token_address)
    deployer_pct = lp.get("deployer_lp_percent", 0.0)
    liquidity    = lp.get("liquidity_usd", 0.0)
    raw_source   = lp.get("source", "mock")
    source       = "real" if raw_source == "dexscreener" else raw_source

    if source == "mock" and liquidity == 0.0:
        return set_data_source(_build(
            "S06", token_address, 0.5,
            check="deployer_lp_percent",
            result={"deployer_lp_percent": None, "liquidity_usd": 0},
            explanation="Deployer LP data unavailable — cannot assess concentration.",
        ), "unavailable")

    score = round(min(deployer_pct, 1.0), 4)
    explanation = (
        f"Deployer controls {deployer_pct * 100:.1f}% of LP tokens "
        f"(pool liquidity: ${liquidity:,.0f}). "
        + (
            "Deployer holds majority of LP — can drain liquidity instantly."
            if score >= 0.5 else
            "Deployer holds significant LP — elevated rug risk."
            if score >= 0.25 else
            "Deployer LP concentration is low — reduced rug risk."
            if score > 0.0 else
            "Deployer LP data unavailable — assuming low concentration."
        )
    )

    return set_data_source(_build(
        "S06", token_address, score,
        check="deployer_lp_percent",
        result={"deployer_lp_percent": deployer_pct, "liquidity_usd": liquidity},
        explanation=explanation,
    ), source)


# ---------------------------------------------------------------------------
#  S08 — Top-10 Holder Concentration
# ---------------------------------------------------------------------------

def signal_08_top10_concentration(token_address: str) -> dict:
    """
    Risk scales with the combined supply % held by the top 10 wallets.
    Extreme concentration = coordinated dump can collapse the price.

    Score: top_10_concentration (capped at 1.0).
    Data: Real — getTokenLargestAccounts + getTokenSupply RPC.
    """
    holders       = get_holder_info(token_address)
    concentration = holders.get("top_10_concentration", 0.0)

    score = round(min(concentration, 1.0), 4)
    explanation = (
        f"Top 10 wallets hold {concentration * 100:.1f}% of total supply. "
        + (
            "Extreme concentration — a coordinated sell would crater the price."
            if score >= 0.8 else
            "High concentration — significant coordinated sell-off risk."
            if score >= 0.5 else
            "Moderate concentration — typical for early-stage tokens."
            if score >= 0.3 else
            "Well-distributed supply — low risk from top-holder coordination."
        )
    )

    return set_data_source(_build(
        "S08", token_address, score,
        check="top_10_holder_concentration",
        result={
            "top_10_concentration": concentration,
            "holders": holders.get("holders", []),
        },
        explanation=explanation,
    ), holders.get("source", "real"))


# ---------------------------------------------------------------------------
#  S09 — Whale Dominance
# ---------------------------------------------------------------------------

def signal_09_whale_dominance(token_address: str) -> dict:
    """
    Focuses on the SINGLE largest holder.
    One wallet with >30% of supply can crash the token at will.

    Score tiers:
        ≥ 50% → 0.95  (extreme dominance)
        ≥ 30% → 0.85
        ≥ 10% → 0.65
        ≥  5% → 0.40
        < 5%  → 0.10
    Data: Real — getTokenLargestAccounts + getTokenSupply RPC.
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
        score = 0.40
    else:
        score = 0.10

    explanation = (
        f"Largest single holder owns {top_pct * 100:.2f}% of supply. "
        + (
            "Single whale dominance — one wallet can collapse the token value."
            if score >= 0.8 else
            "Significant whale — large coordinated sell is a serious risk."
            if score >= 0.6 else
            "Moderate whale presence — manageable but worth monitoring."
            if score >= 0.35 else
            "No single whale dominance — healthy holder distribution."
        )
    )

    return set_data_source(_build(
        "S09", token_address, score,
        check="top_holder_percent",
        result={"top_holder_percent": top_pct,
                "all_holders": holders.get("holders", [])},
        explanation=explanation,
    ), holders.get("source", "real"))


# ---------------------------------------------------------------------------
#  Convenience: run all S01–S09 signals
# ---------------------------------------------------------------------------

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
    """Run S01–S09 for a given token address. Returns list of signal dicts."""
    results = []
    for fn in ALL_SIGNALS:
        try:
            results.append(fn(token_address))
        except Exception as e:
            # Last-resort safety net — a signal must never kill the scorer
            print(f"  [WARN] {fn.__name__} raised an unexpected error: {e}")
    return results
