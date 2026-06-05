"""
graph_analyzer/deployer_fetcher.py — Fetches wallet transactions and age from Solana mainnet.

Uses the real Solana mainnet RPC (not devnet).
Provides:
    get_wallet_transactions(wallet, limit) → list of signature objects
    get_wallet_age_days(wallet)            → int (days since oldest tx)
    get_deployer_wallet(token_address)     → str (fee payer of first mint tx)
"""

import time
import requests

# ---------------------------------------------------------------------------
#  RPC config — reads from environment or falls back to public mainnet
# ---------------------------------------------------------------------------

import os
import sys
from pathlib import Path

# Allow standalone execution from graph_analyzer/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import SOLANA_RPC_URL
except ImportError:
    # Fallback if called standalone
    SOLANA_RPC_URL = os.getenv(
        "SOLANA_RPC_URL",
        "https://api.mainnet-beta.solana.com",
    )

_SESSION = requests.Session()
_SESSION.headers.update({"Content-Type": "application/json"})

_MAX_RETRIES = 2
_TIMEOUT     = 12


# ---------------------------------------------------------------------------
#  Low-level RPC helper
# ---------------------------------------------------------------------------

def _rpc(method: str, params: list) -> dict | list | None:
    """Fire a JSON-RPC request. Retries once on transient failure."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _SESSION.post(SOLANA_RPC_URL, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return None
            return data.get("result")
        except Exception as e:
            if attempt == _MAX_RETRIES - 1:
                print(f"  [WARN] deployer_fetcher RPC failed ({method}): {e}")
            time.sleep(0.3 * (attempt + 1))
    return None


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def get_wallet_transactions(wallet_address: str, limit: int = 100) -> list:
    """
    Fetch recent transaction signatures for a wallet.
    Returns a list of signature objects (newest first).
    Each object has: signature, slot, blockTime, err, memo.
    """
    result = _rpc(
        "getSignaturesForAddress",
        [wallet_address, {"limit": min(limit, 1000), "commitment": "confirmed"}],
    )
    if isinstance(result, list):
        return result
    return []


def get_wallet_age_days(wallet_address: str) -> int:
    """
    Calculate wallet age in days from its oldest on-chain transaction.

    Returns 0 if no transactions found (treated as brand-new = high risk).
    Uses up to 1000 signatures to find the oldest activity.
    """
    txs = get_wallet_transactions(wallet_address, limit=1000)
    if not txs:
        return 0

    # Signatures are returned newest-first; oldest is the last element
    oldest_tx        = txs[-1]
    oldest_timestamp = oldest_tx.get("blockTime", 0)

    if not oldest_timestamp:
        return 0

    age_seconds = int(time.time()) - oldest_timestamp
    return max(0, age_seconds // 86_400)   # 86_400 s/day


def get_deployer_wallet(token_address: str) -> str:
    """
    Identify the deployer wallet by finding the fee payer (account[0])
    of the oldest transaction on the token mint account.

    This is the wallet that paid for the InitializeMint instruction,
    i.e. the person who actually created the token.

    Falls back to returning token_address itself if lookup fails.
    """
    sigs = get_wallet_transactions(token_address, limit=1000)
    if not sigs:
        return token_address

    oldest_sig = sigs[-1].get("signature", "")
    if not oldest_sig:
        return token_address

    tx_result = _rpc(
        "getTransaction",
        [oldest_sig, {
            "encoding":                       "jsonParsed",
            "commitment":                     "confirmed",
            "maxSupportedTransactionVersion": 0,
        }],
    )

    if tx_result:
        try:
            account_keys = (
                tx_result.get("transaction", {})
                          .get("message", {})
                          .get("accountKeys", [])
            )
            if account_keys:
                first = account_keys[0]
                # jsonParsed encoding returns objects; raw returns plain strings
                if isinstance(first, dict):
                    return first.get("pubkey", token_address)
                return str(first)
        except Exception:
            pass

    return token_address


# ---------------------------------------------------------------------------
#  Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Testing deployer_fetcher on wallet: {test_wallet}\n")

    txs = get_wallet_transactions(test_wallet, limit=5)
    print(f"  Recent transactions found : {len(txs)}")

    age = get_wallet_age_days(test_wallet)
    print(f"  Wallet age                : {age} days")

    if age < 7:
        print("  🚩 CRITICAL: Wallet is less than 7 days old")
    elif age < 30:
        print("  🚩 HIGH RISK: Wallet is less than 30 days old")
    else:
        print("  ✅ Wallet has an established history")
