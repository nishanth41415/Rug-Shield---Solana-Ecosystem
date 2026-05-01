"""
Solana RPC helpers.
Falls back to deterministic mock data when RPC is unreachable
(useful for offline dev / hackathon testing).
"""

import hashlib
import requests
from config import SOLANA_RPC_URL


# --------------------------------------------------------------------------- #
#  Low-level RPC                                                               #
# --------------------------------------------------------------------------- #

def _rpc(method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        r = requests.post(SOLANA_RPC_URL, json=payload, timeout=10)
        r.raise_for_status()
        return r.json().get("result", {})
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
#  Mock data generator (deterministic from address hash)                      #
# --------------------------------------------------------------------------- #

def _mock_seed(address: str) -> int:
    """Stable pseudo-random seed derived from token address."""
    return int(hashlib.sha256(address.encode()).hexdigest(), 16)


def _mock_account_info(address: str) -> dict:
    seed = _mock_seed(address)
    # Even seed → mint authority disabled (safer token)
    has_mint_auth   = bool(seed % 3)          # ~66 % have mint auth
    has_freeze_auth = bool(seed % 4)          # ~75 % have freeze auth
    upgradeable     = bool(seed % 5)          # ~80 % upgradeable
    mutable_meta    = bool(seed % 2)          # 50 % mutable metadata

    return {
        "mint_authority":   "AuthorityPubkey111" if has_mint_auth else None,
        "freeze_authority": "AuthorityPubkey222" if has_freeze_auth else None,
        "upgradeable":      upgradeable,
        "mutable_metadata": mutable_meta,
    }


def _mock_lp_info(address: str) -> dict:
    seed = _mock_seed(address)
    locked_pct    = (seed % 101) / 100          # 0 – 100 %
    deployer_pct  = (seed % 80)  / 100          # 0 – 79 %
    return {
        "lp_locked_percent":   round(locked_pct, 4),
        "deployer_lp_percent": round(deployer_pct, 4),
    }


def _mock_holder_info(address: str) -> dict:
    seed = _mock_seed(address)
    # Generate 10 holder percentages that sum ≤ 100
    holders = []
    remaining = 1.0
    for i in range(10):
        share = round(((seed >> i) % 20) / 100, 4)
        share = min(share, remaining)
        holders.append(share)
        remaining -= share
        if remaining <= 0:
            break
    holders.sort(reverse=True)
    return {
        "top_10_concentration": round(sum(holders), 4),
        "top_holder_percent":   holders[0] if holders else 0.0,
        "holders":              holders,
    }


# --------------------------------------------------------------------------- #
#  Public API (tries real RPC, falls back to mock)                            #
# --------------------------------------------------------------------------- #

def get_account_info(address: str) -> dict:
    result = _rpc("getAccountInfo", [address, {"encoding": "jsonParsed"}])
    if result and result.get("value"):
        parsed = result["value"].get("data", {}).get("parsed", {}).get("info", {})
        if parsed:
            return {
                "mint_authority":   parsed.get("mintAuthority"),
                "freeze_authority": parsed.get("freezeAuthority"),
                "upgradeable":      parsed.get("isInitialized", False),
                "mutable_metadata": True,   # needs separate Metaplex call
            }
    # Fallback
    return _mock_account_info(address)


def get_lp_info(address: str) -> dict:
    """LP lock / deployer concentration — mock until LP indexer is wired."""
    return _mock_lp_info(address)


def get_holder_info(address: str) -> dict:
    """Holder distribution — mock until holder indexer is wired."""
    return _mock_holder_info(address)
