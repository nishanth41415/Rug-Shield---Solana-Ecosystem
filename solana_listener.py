"""
solana_listener.py — Real-time Solana new token mint detector.

Listens for new SPL token InitializeMint instructions via:
  1. WebSocket (WSS) — primary, real-time via logsSubscribe
  2. HTTP polling   — fallback if WebSocket is unavailable

When a new mint is detected, the token address is pushed to the Redis
`token_events` queue so consumer.py can pick it up and score it.

Usage:
    python3 solana_listener.py               # WSS mode (real-time)
    python3 solana_listener.py --poll        # HTTP polling fallback
    python3 solana_listener.py --poll --interval 30  # poll every 30 seconds

Requirements:
    pip install websocket-client redis requests

TODO: Replace SOLANA_WSS_URL in config.py with your premium WSS endpoint
      for reliable real-time detection (public endpoint may drop connections).
"""

import json
import sys
import time
import argparse
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import SOLANA_RPC_URL, SOLANA_WSS_URL, SPL_TOKEN_PROGRAM_ID, REDIS_QUEUE_KEY


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _push_to_redis(token_address: str, deployer: str = ""):
    """Push a mint event to the Redis token_events queue."""
    try:
        import redis
        from config import REDIS_HOST, REDIS_PORT, REDIS_DB
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                        decode_responses=True)
        event = {
            "event_type":    "mint",
            "token_address": token_address,
            "deployer":      deployer,
            "timestamp":     _now(),
        }
        r.rpush(REDIS_QUEUE_KEY, json.dumps(event))
        print(f"  [{_now()}] 📨 Pushed to Redis queue: {token_address[:16]}...")
    except Exception as e:
        print(f"  [WARN] Redis push failed: {e}")


def _extract_mint_from_logs(logs: list[str], accounts: list[str]) -> str | None:
    """
    Extract the newly initialized mint address from transaction logs + accounts.

    The InitializeMint instruction from the SPL Token program logs:
        "Program log: Instruction: InitializeMint"

    The mint account is account[0] in the transaction's account keys
    when InitializeMint is called.
    """
    has_init_mint = any(
        "InitializeMint" in log or "InitializeMint2" in log
        for log in (logs or [])
    )
    if not has_init_mint:
        return None

    # The mint account address is typically the first non-signer account
    for acct in (accounts or []):
        if acct and len(acct) > 30:
            return acct

    return None


# ---------------------------------------------------------------------------
#  Mode 1: WebSocket real-time listener
# ---------------------------------------------------------------------------

def _wss_listener(stop_event: threading.Event):
    """
    Subscribe to Solana logs via WebSocket.
    Filters for transactions that mention the SPL Token program
    and contain an InitializeMint instruction.

    Reconnects automatically on disconnect.
    """
    try:
        import websocket  # type: ignore
    except ImportError:
        print("[ERROR] websocket-client not installed.")
        print("        Run:  pip install websocket-client")
        sys.exit(1)

    subscription_msg = json.dumps({
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "logsSubscribe",
        "params": [
            {"mentions": [SPL_TOKEN_PROGRAM_ID]},
            {"commitment": "confirmed"},
        ],
    })

    backoff = 1
    max_backoff = 16

    while not stop_event.is_set():
        print(f"[{_now()}] Connecting to WebSocket...")
        try:
            ws = websocket.create_connection(SOLANA_WSS_URL, timeout=30)
            backoff = 1
            ws.send(subscription_msg)
            print(f"[{_now()}] ✅ WebSocket connected. Watching for new token mints...")

            while not stop_event.is_set():
                try:
                    ws.settimeout(10)
                    raw = ws.recv()
                    if not raw:
                        continue

                    msg = json.loads(raw)

                    # Subscription confirmation
                    if "result" in msg and isinstance(msg["result"], int):
                        print(f"[{_now()}] Subscription ID: {msg['result']}")
                        continue

                    # Log notification
                    params = msg.get("params", {})
                    result = params.get("result", {})
                    value  = result.get("value", {})

                    logs     = value.get("logs", [])
                    accounts = []

                    # Try to get account keys from the notification
                    tx_info = value.get("transaction", {})
                    if tx_info:
                        msg_data = tx_info.get("message", {})
                        accounts = msg_data.get("accountKeys", [])
                        if accounts and isinstance(accounts[0], dict):
                            accounts = [a.get("pubkey", "") for a in accounts]

                    mint = _extract_mint_from_logs(logs, accounts)
                    if mint:
                        print(f"[{_now()}] 🪙 New token mint detected: {mint}")
                        _push_to_redis(mint)

                except websocket.WebSocketTimeoutException:
                    continue   # normal — just no messages in 10s
                except Exception as e:
                    print(f"[{_now()}] [WARN] WS recv error: {e}")
                    break

            ws.close()

        except Exception as e:
            print(f"[{_now()}] [ERROR] WebSocket connection failed: {e}")
            if not stop_event.is_set():
                print(f"[{_now()}] Reconnecting in {backoff} seconds...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)


def run_wss_listener():
    """Start the WebSocket listener with graceful Ctrl+C shutdown."""
    stop_event = threading.Event()
    thread     = threading.Thread(target=_wss_listener, args=(stop_event,), daemon=True)
    thread.start()

    try:
        while thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{_now()}] Shutting down WebSocket listener...")
        stop_event.set()
        thread.join(timeout=5)
        print(f"[{_now()}] Stopped.")


# ---------------------------------------------------------------------------
#  Mode 2: HTTP polling fallback
# ---------------------------------------------------------------------------

def _get_recent_token_txs(before_sig: str | None = None) -> list[dict]:
    """
    Fetch recent signatures on the SPL Token program via HTTP RPC.
    Used for polling mode — scans for InitializeMint transactions.
    """
    import requests
    params: list = [SPL_TOKEN_PROGRAM_ID, {"limit": 50, "commitment": "confirmed"}]
    if before_sig:
        params[1]["before"] = before_sig

    try:
        resp = requests.post(
            SOLANA_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1,
                  "method": "getSignaturesForAddress", "params": params},
            timeout=15,
        )
        data = resp.json()
        return data.get("result", []) or []
    except Exception as e:
        print(f"  [WARN] HTTP poll failed: {e}")
        return []


def _check_tx_for_mint(signature: str) -> str | None:
    """
    Fetch a full transaction and check if it contains InitializeMint.
    Returns the mint address if found, else None.
    """
    import requests
    try:
        resp = requests.post(
            SOLANA_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1,
                  "method": "getTransaction",
                  "params": [signature, {
                      "encoding": "jsonParsed",
                      "commitment": "confirmed",
                      "maxSupportedTransactionVersion": 0,
                  }]},
            timeout=15,
        )
        tx = resp.json().get("result")
        if not tx:
            return None

        meta = tx.get("meta", {})
        logs = meta.get("logMessages", [])

        account_keys = (
            tx.get("transaction", {})
              .get("message", {})
              .get("accountKeys", [])
        )
        accounts = []
        for k in account_keys:
            pubkey = k.get("pubkey", k) if isinstance(k, dict) else k
            accounts.append(pubkey)

        return _extract_mint_from_logs(logs, accounts)
    except Exception:
        return None


def run_http_poll(interval: int = 15):
    """
    Poll the SPL Token program every `interval` seconds for new InitializeMint txs.
    Fallback for when WebSocket is unavailable.
    """
    print(f"[{_now()}] Starting HTTP polling mode (every {interval}s)...")
    print(f"[{_now()}] Watching SPL Token program for new mints...")
    seen_sigs: set = set()
    last_sig: str | None  = None

    while True:
        try:
            sigs = _get_recent_token_txs(before_sig=None)

            new_sigs = [s for s in sigs if s.get("signature") not in seen_sigs]
            if new_sigs:
                # Process newest sigs first
                for sig_obj in new_sigs[:10]:
                    sig = sig_obj.get("signature", "")
                    if not sig:
                        continue
                    seen_sigs.add(sig)
                    mint = _check_tx_for_mint(sig)
                    if mint:
                        print(f"[{_now()}] 🪙 New token mint: {mint}")
                        _push_to_redis(mint)
                    time.sleep(0.2)

            print(f"[{_now()}] Poll complete. Sleeping {interval}s...")
            time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n[{_now()}] HTTP polling stopped.")
            break
        except Exception as e:
            print(f"[{_now()}] [ERROR] Poll loop error: {e}")
            time.sleep(interval)


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RugShield P2 — Solana new token mint listener"
    )
    parser.add_argument(
        "--poll", action="store_true",
        help="Use HTTP polling instead of WebSocket (fallback mode)",
    )
    parser.add_argument(
        "--interval", type=int, default=15,
        help="Polling interval in seconds (only used with --poll, default: 15)",
    )
    args = parser.parse_args()

    if args.poll:
        run_http_poll(interval=args.interval)
    else:
        if not SOLANA_WSS_URL:
            print("[ERROR] SOLANA_WSS_URL is not set. Add it to .env or run with --poll.")
            sys.exit(1)
        run_wss_listener()
