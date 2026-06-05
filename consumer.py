"""
consumer.py — Redis consumer for RugShield P2 scoring engine.

Reads mint events from the `token_events` Redis queue,
runs the full scoring pipeline (all 18 signals + ML model),
and writes per-token JSON results to ./output/.

Usage:
    python3 consumer.py                  # live mode (blocking pop, runs forever)
    python3 consumer.py --once           # process one message and exit
    python3 consumer.py --dry-run        # no Redis needed, scores TEST_ADDRESS
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

OUTPUT_DIR   = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Default test address — Wrapped SOL (well-known, should score LOW)
TEST_ADDRESS = "So11111111111111111111111111111111111111112"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
#  Event processor — runs the full scoring pipeline
# ---------------------------------------------------------------------------

def process_event(event: dict) -> dict | None:
    """
    Score a token from a mint event dict.

    Expected event shape:
        {
            "event_type":    "mint",
            "token_address": "<base58 mint address>",
            "deployer":      "<base58 wallet>",   (optional hint)
            "timestamp":     "<ISO 8601>"
        }

    Writes:
        output/<token_prefix>_score.json   — full scorer output
    """
    from scorer import is_valid_solana_address, score_token

    token_address = event.get("token_address", TEST_ADDRESS)
    if not isinstance(token_address, str) or not token_address.strip():
        print(f"[{_now()}] [WARN] Missing token_address in event — skipping")
        return None
    token_address = token_address.strip()
    if not is_valid_solana_address(token_address):
        print(f"[{_now()}] [WARN] Invalid token_address — skipping")
        return None

    print(f"\n[{_now()}] Processing token: {token_address}")

    try:
        result = score_token(token_address)
    except Exception as e:
        print(f"  [ERROR] Scoring failed: {e}")
        return None

    # Write full output JSON
    out_path = OUTPUT_DIR / f"{token_address[:8]}_score.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    risk  = result.get("risk_level", "UNKNOWN")
    score = result.get("risk_score", 0)
    print(f"  ✅ Score: {score}/100  Risk: {risk}  → {out_path.name}")

    return result


# ---------------------------------------------------------------------------
#  Dry-run mode (no Redis required)
# ---------------------------------------------------------------------------

def dry_run():
    print("=== DRY RUN MODE (no Redis required) ===")
    fake_event = {
        "event_type":    "mint",
        "token_address": TEST_ADDRESS,
        "deployer":      "",
        "timestamp":     _now(),
    }
    print(f"Fake event: {json.dumps(fake_event, indent=2)}\n")
    process_event(fake_event)


# ---------------------------------------------------------------------------
#  Live Redis consumer
# ---------------------------------------------------------------------------

def run_consumer(once: bool = False):
    import redis
    from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_QUEUE_KEY

    r = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
        decode_responses=True,
    )

    try:
        r.ping()
        print(f"[{_now()}] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to Redis: {e}")
        print("Tip: start Redis with  docker run -p 6379:6379 redis:alpine")
        sys.exit(1)

    print(f"[{_now()}] Listening on queue '{REDIS_QUEUE_KEY}' ...")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            # BLPOP blocks up to 5s then loops — allows clean Ctrl+C
            item = r.blpop(REDIS_QUEUE_KEY, timeout=5)
            if item is None:
                continue   # timeout, keep waiting

            _, raw = item

            try:
                event = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"[WARN] Bad JSON in queue: {e} — skipping")
                continue

            process_event(event)

            if once:
                print(f"[{_now()}] --once flag set. Exiting.")
                break

        except KeyboardInterrupt:
            print(f"\n[{_now()}] Consumer stopped.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RugShield P2 — Redis scoring consumer")
    parser.add_argument("--once",    action="store_true",
                        help="Process one message from the queue and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Redis and score a test token address")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        run_consumer(once=args.once)
