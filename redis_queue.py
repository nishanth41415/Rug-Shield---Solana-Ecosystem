"""
redis_queue.py — Redis List queue helpers for mint events.

Uses Redis Lists (RPUSH / BLPOP) on REDIS_QUEUE_KEY — same as consumer.py
and solana_listener.py. Do not use Redis Streams here.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_QUEUE_KEY


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redis_client():
    import redis
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
        decode_responses=True,
    )


def push_mint_event(token_address: str, deployer: str = "") -> None:
    """Push a mint event to the token_events Redis list."""
    r = _redis_client()
    event = {
        "event_type":    "mint",
        "token_address": token_address,
        "deployer":      deployer,
        "timestamp":     _now(),
    }
    r.rpush(REDIS_QUEUE_KEY, json.dumps(event))
    print(f"Pushed mint event: {token_address}")


def pop_mint_event(timeout: int = 1) -> dict | None:
    """Block-pop one mint event from the queue (matches consumer.py BLPOP)."""
    r = _redis_client()
    item = r.blpop(REDIS_QUEUE_KEY, timeout=timeout)
    if item is None:
        return None
    _, raw = item
    return json.loads(raw)


def read_mint_events(count: int = 10) -> list[dict]:
    """Peek at up to `count` events without removing them."""
    r = _redis_client()
    raw_items = r.lrange(REDIS_QUEUE_KEY, 0, count - 1)
    return [json.loads(item) for item in raw_items]


if __name__ == "__main__":
    print(f"Testing Redis List queue '{REDIS_QUEUE_KEY}'...")

    test_addresses = [
        "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "9yKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgBsV",
        "3zKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgCsW",
    ]

    r = _redis_client()
    try:
        r.ping()
    except Exception as e:
        print(f"[ERROR] Cannot connect to Redis: {e}")
        print("Tip: docker-compose up -d redis")
        sys.exit(1)

    for addr in test_addresses:
        push_mint_event(addr)

    print(f"\nQueue length: {r.llen(REDIS_QUEUE_KEY)}")
    print("Events in queue:")
    for event in read_mint_events():
        print(f"  {event.get('token_address')}")

    popped = pop_mint_event(timeout=1)
    if popped:
        print(f"\nBLPOP test OK: {popped.get('token_address')}")
