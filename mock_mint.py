"""
mock_mint.py — Push a fake mint event into Redis for testing.

Usage:
    python mock_mint.py                            # uses default address
    python mock_mint.py <token_address>            # custom address
    python mock_mint.py --count 5                  # push 5 fake events
"""

import json
import sys
import argparse
from datetime import datetime, timezone

DEFAULT_ADDRESS = "So11111111111111111111111111111111111111112"
FAKE_ADDRESSES = [
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
]


def push_event(r, address: str, queue_key: str):
    event = {
        "event_type":    "mint",
        "token_address": address,
        "deployer":      "DeployerPubkey111111111111111111111111111",
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(queue_key, json.dumps(event))
    print(f"✔ Pushed mint event for {address}")
    return event


def main():
    parser = argparse.ArgumentParser(description="Push fake mint events to Redis")
    parser.add_argument("address", nargs="?", default=None)
    parser.add_argument("--count", type=int, default=1,
                        help="Number of events to push (uses preset addresses)")
    args = parser.parse_args()

    try:
        import redis
    except ImportError:
        print("Run: pip install redis --break-system-packages")
        sys.exit(1)

    try:
        from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_QUEUE_KEY
    except ImportError:
        REDIS_HOST, REDIS_PORT, REDIS_DB = "localhost", 6379, 0
        REDIS_QUEUE_KEY = "token_events"

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                    decode_responses=True)

    try:
        r.ping()
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to Redis: {e}")
        print("Start Redis:  docker run -d -p 6379:6379 redis:alpine")
        sys.exit(1)

    if args.address:
        push_event(r, args.address, REDIS_QUEUE_KEY)
    else:
        addresses = (FAKE_ADDRESSES * ((args.count // len(FAKE_ADDRESSES)) + 1))[:args.count]
        for addr in addresses:
            push_event(r, addr, REDIS_QUEUE_KEY)

    queue_len = r.llen(REDIS_QUEUE_KEY)
    print(f"\nQueue '{REDIS_QUEUE_KEY}' now has {queue_len} item(s).")
    print("Run consumer.py to process them.")


if __name__ == "__main__":
    main()
