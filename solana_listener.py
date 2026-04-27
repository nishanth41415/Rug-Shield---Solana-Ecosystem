import redis
import json
import time
from solana.rpc.api import Client
from solders.pubkey import Pubkey

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Connect to Solana devnet
solana_client = Client("https://api.devnet.solana.com")

# SPL Token Program ID
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

def push_to_redis(mint_address, program_id):
    """Push mint event to Redis Streams"""
    event = {
        "mintAddress": mint_address,
        "timestamp": int(time.time()),
        "programId": program_id
    }
    r.xadd("solana:mint:events", event)
    print(f"✅ New mint detected and queued: {mint_address}")

def listen_for_mints():
    """Listen for new token mint events on Solana devnet"""
    print("🔍 Listening for new Solana token mints on devnet...")
    print("Press Ctrl+C to stop\n")
    
    last_slot = solana_client.get_slot().value
    
    while True:
        try:
            # Get current slot
            current_slot = solana_client.get_slot().value
            
            if current_slot > last_slot:
                # Get recent transactions for Token Program
                signatures = solana_client.get_signatures_for_address(
                    Pubkey.from_string(TOKEN_PROGRAM_ID),
                    limit=5
                ).value
                
                for sig in signatures:
                    tx = solana_client.get_transaction(
                        sig.signature,
                        max_supported_transaction_version=0
                    ).value
                    
                    if tx and tx.transaction:
                        # Extract mint address from transaction
                        accounts = tx.transaction.transaction.message.account_keys
                        for account in accounts:
                            account_str = str(account)
                            if len(account_str) == 44:
                                push_to_redis(account_str, TOKEN_PROGRAM_ID)
                                break
                
                last_slot = current_slot
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n⛔ Listener stopped")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    listen_for_mints()
