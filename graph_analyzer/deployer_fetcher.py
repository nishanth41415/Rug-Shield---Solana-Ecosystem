"""
deployer_fetcher.py — Fetches wallet transactions and age from Solana.

Fixed from P1's original:
  - Changed RPC from devnet → mainnet-beta (real tokens live on mainnet)
  - Added graceful fallback if RPC fails
  - Added get_deployer_wallet() helper for scorer.py
"""

import requests
import time

# Mainnet — real tokens are here, not devnet
SOLANA_RPC = "https://api.mainnet-beta.solana.com"


def get_wallet_transactions(wallet_address, limit=100):
    """Fetch transaction history for a wallet."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }

    try:
        response = requests.post(SOLANA_RPC, json=payload, timeout=10)
        result = response.json()

        if "result" in result:
            return result["result"]
        else:
            print(f"⚠️ No transactions found for {wallet_address}")
            return []
    except Exception as e:
        print(f"❌ Error fetching wallet: {e}")
        return []


def get_wallet_age_days(wallet_address):
    """Calculate wallet age in days from oldest transaction."""
    transactions = get_wallet_transactions(wallet_address, limit=1000)

    if not transactions:
        # Cannot determine age — return 0 (treated as brand new = high risk)
        return 0

    oldest_tx = transactions[-1]
    oldest_timestamp = oldest_tx.get("blockTime", 0)

    if oldest_timestamp == 0:
        return 0

    current_timestamp = int(time.time())
    age_seconds = current_timestamp - oldest_timestamp
    age_days = age_seconds // (60 * 60 * 24)

    return int(age_days)


def get_deployer_wallet(token_address: str) -> str:
    """
    Get the deployer wallet for a token by finding the first
    transaction that created/initialized the mint account.
    Falls back to using the token address itself if lookup fails.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [token_address, {"limit": 1000}]
    }

    try:
        response = requests.post(SOLANA_RPC, json=payload, timeout=10)
        result = response.json()

        if "result" in result and result["result"]:
            # Oldest transaction = deployment tx
            oldest = result["result"][-1]
            sig = oldest.get("signature", "")
            if sig:
                # Fetch the actual transaction to get the fee payer (deployer)
                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                }
                tx_resp = requests.post(SOLANA_RPC, json=tx_payload, timeout=10)
                tx_data = tx_resp.json()
                account_keys = (
                    tx_data.get("result", {})
                    .get("transaction", {})
                    .get("message", {})
                    .get("accountKeys", [])
                )
                if account_keys:
                    return account_keys[0]  # fee payer = deployer
    except Exception:
        pass

    # Fallback — use token address as proxy
    return token_address


# Test
if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Testing wallet fetcher on: {test_wallet}\n")

    txs = get_wallet_transactions(test_wallet, limit=5)
    print(f"✅ Found {len(txs)} transactions")

    age = get_wallet_age_days(test_wallet)
    print(f"📅 Wallet age: {age} days")

    if age < 30:
        print("🚩 WARNING: Wallet is less than 30 days old - HIGH RISK")
