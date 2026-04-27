import redis
import json
import time

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def push_mint_event(mint_address, program_id):
    """Push a new token mint event to Redis Streams"""
    event = {
        "mintAddress": mint_address,
        "timestamp": int(time.time()),
        "programId": program_id
    }
    # Push to Redis Stream
    r.xadd("solana:mint:events", event)
    print(f"✅ Pushed mint event: {mint_address}")

def read_mint_events():
    """Read all mint events from Redis Streams"""
    events = r.xread({"solana:mint:events": "0"}, count=10)
    if events:
        for stream, messages in events:
            for msg_id, msg_data in messages:
                print(f"📨 Event: {msg_data}")
    else:
        print("No events in queue yet")

# Test it with a fake mint address
if __name__ == "__main__":
    print("Testing Redis Streams queue...")
    
    # Push 3 fake mint events
    push_mint_event("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    push_mint_event("9yKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgBsV", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    push_mint_event("3zKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgCsW", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    
    print("\nReading events from queue:")
    read_mint_events()
