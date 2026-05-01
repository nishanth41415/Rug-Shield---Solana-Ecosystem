"""
Redis consumer — reads mint events from the `token_events` queue,
runs all signals, and writes per-signal JSON to ./output/.

Usage:
    python consumer.py                  # live mode (blocking pop)
    python consumer.py --once           # process one message and exit
    python consumer.py --dry-run        # no Redis needed, uses TEST_ADDRESS
"""

import json
import sys
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root when running from any working directory
sys.path.insert(0, str(Path(__file__).parent))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TEST_ADDRESS = "So11111111111111111111111111111111111111112"  # Wrapped SOL


def process_event(event: dict) -> list[dict]:
    """Run all signals for a token_address from a mint event."""
    from signals.signals import run_all_signals

    token_address = event.get("token_address", TEST_ADDRESS)
    print(f"\n[{_now()}] Processing token: {token_address}")

    results = run_all_signals(token_address)

    # Write output files
    for signal in results:
        sid = signal["signal_id"]
        filename = OUTPUT_DIR / f"{token_address[:8]}_{sid}.json"
        with open(filename, "w") as f:
            json.dump(signal, f, indent=2)
        risk = signal["risk_level"]
        score = signal["score"]
        print(f"  {sid}  score={score:.4f}  risk={risk:8s}  → {filename.name}")

    # Also write a combined file
    combined_path = OUTPUT_DIR / f"{token_address[:8]}_all_signals.json"
    with open(combined_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Combined → {combined_path.name}")

    return results


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
#  Dry-run mode (no Redis)                                                     #
# --------------------------------------------------------------------------- #

def dry_run():
    print("=== DRY RUN MODE (no Redis required) ===")
    fake_event = {
        "event_type":    "mint",
        "token_address": TEST_ADDRESS,
        "deployer":      "DeployerPubkey111111111111111111111111111",
        "timestamp":     _now(),
    }
    print(f"Fake event: {json.dumps(fake_event, indent=2)}")
    process_event(fake_event)


# --------------------------------------------------------------------------- #
#  Live Redis consumer                                                         #
# --------------------------------------------------------------------------- #

def run_consumer(once: bool = False):
    import redis
    from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_QUEUE_KEY

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                    decode_responses=True)

    try:
        r.ping()
    except Exception as e:
        print(f"[ERROR] Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}")
        print("Tip: start Redis with  docker run -p 6379:6379 redis:alpine")
        sys.exit(1)

    print(f"[{_now()}] Consumer started. Listening on queue '{REDIS_QUEUE_KEY}' ...")

    while True:
        try:
            # BLPOP blocks (timeout=5 s so we can Ctrl+C cleanly)
            item = r.blpop(REDIS_QUEUE_KEY, timeout=5)
            if item is None:
                continue  # timeout, loop again

            _, raw = item
            event = json.loads(raw)
            process_event(event)

            if once:
                break

        except KeyboardInterrupt:
            print("\nConsumer stopped.")
            break
        except json.JSONDecodeError as e:
            print(f"[WARN] Bad JSON in queue: {e}")
        except Exception as e:
            print(f"[ERROR] {e}")


# --------------------------------------------------------------------------- #
#  Entry point                                                                 #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Token scoring Redis consumer")
    parser.add_argument("--once",    action="store_true", help="Process one message and exit")
    parser.add_argument("--dry-run", action="store_true", help="Skip Redis, use fake event")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        run_consumer(once=args.once)
