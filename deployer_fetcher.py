import requests
import time

SOLANA_RPC = "https://api.devnet.solana.com"

def get_wallet_transactions(wallet_address, limit=100):
    """Fetch transaction history for a wallet"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": limit}]
    }
    
    try:
        response = requests.post(SOLANA_RPC, json=payload)
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
    """Calculate wallet age in days"""
    transactions = get_wallet_transactions(wallet_address, limit=1000)
    
    if not transactions:
        return 0
    
    # Oldest transaction timestamp
    oldest_tx = transactions[-1]
    oldest_timestamp = oldest_tx.get("blockTime", 0)
    
    current_timestamp = int(time.time())
    age_seconds = current_timestamp - oldest_timestamp
    age_days = age_seconds // (60 * 60 * 24)
    
    return age_days

# Test it
if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Testing wallet fetcher on: {test_wallet}\n")
    
    txs = get_wallet_transactions(test_wallet, limit=5)
    print(f"✅ Found {len(txs)} transactions")
    
    age = get_wallet_age_days(test_wallet)
    print(f"📅 Wallet age: {age} days")
    
    if age < 30:
        print("🚩 WARNING: Wallet is less than 30 days old - HIGH RISK")
