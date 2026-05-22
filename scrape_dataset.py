"""
scrape_dataset.py — Collect labeled token data from RugCheck + Solsniffer.

Saves a CSV to data/labeled_tokens.csv with one row per token.
Each row has 18 signal scores + a label (1=scam, 0=safe).

Usage:
    python scrape_dataset.py             # scrape + score everything
    python scrape_dataset.py --mock      # skip real API calls, use mock data only
    python scrape_dataset.py --count 200 # how many tokens to collect (default 500)

The CSV is what train_model.py reads to train the ML model.
"""

import csv
import json
import time
import argparse
import hashlib
import requests
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

OUTPUT_PATH = Path(__file__).parent / "data" / "labeled_tokens.csv"

# CSV columns — 18 signal scores + label + address
COLUMNS = [
    "token_address",
    "s01_mint_authority",
    "s02_freeze_authority",
    "s03_upgradeable",
    "s04_metadata_mutable",
    "s05_lp_lock",
    "s06_deployer_lp",
    "s08_top10_holders",
    "s09_whale_dominance",
    "s10_sybil_clusters",
    "s11_rug_history",
    "s12_wallet_age",
    "s13_suspicious_tx",
    "s14_bot_spike",
    "s15_wash_trading",
    "s16_insider_dump",
    "s17_social_verify",
    "s18_fake_engagement",
    "label",   # 1 = scam, 0 = safe
    "source",  # rugcheck | solsniffer | mock
]


# ------------------------------------------------------------------ #
#  Real API scrapers                                                  #
# ------------------------------------------------------------------ #

def fetch_rugcheck_tokens(limit: int = 250) -> list[dict]:
    """
    Fetch recently flagged (scam) and recently passed (safe) tokens
    from RugCheck's public API.
    Returns list of {"address": str, "label": int}
    """
    tokens = []

    # Scam tokens — recently rugged
    try:
        print("Fetching scam tokens from RugCheck...")
        url = "https://api.rugcheck.xyz/v1/stats/recent"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for item in data[:limit // 2]:
                addr = item.get("mint") or item.get("address")
                if addr:
                    tokens.append({"address": addr, "label": 1, "source": "rugcheck"})
            print(f"  Got {len(tokens)} scam tokens from RugCheck")
    except Exception as e:
        print(f"  RugCheck scam fetch failed: {e}")

    # Safe tokens — passed rugcheck
    try:
        url = "https://api.rugcheck.xyz/v1/stats/new_tokens"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            safe = []
            for item in data[:limit // 2]:
                addr = item.get("mint") or item.get("address")
                score = item.get("score", 100)
                # RugCheck score > 80 = considered safe
                if addr and score > 80:
                    safe.append({"address": addr, "label": 0, "source": "rugcheck"})
            tokens.extend(safe)
            print(f"  Got {len(safe)} safe tokens from RugCheck")
    except Exception as e:
        print(f"  RugCheck safe fetch failed: {e}")

    return tokens


def fetch_solsniffer_tokens(limit: int = 250) -> list[dict]:
    """
    Fetch tokens from Solsniffer's public endpoint.
    Solsniffer score < 30 = scam, > 70 = safe.
    """
    tokens = []
    try:
        print("Fetching tokens from Solsniffer...")
        url = "https://solsniffer.com/api/v2/tokens/recent"
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        if r.status_code == 200:
            data = r.json()
            items = data if isinstance(data, list) else data.get("tokens", [])
            for item in items[:limit]:
                addr  = item.get("address") or item.get("mint")
                score = item.get("score", 50)
                if not addr:
                    continue
                if score < 30:
                    tokens.append({"address": addr, "label": 1, "source": "solsniffer"})
                elif score > 70:
                    tokens.append({"address": addr, "label": 0, "source": "solsniffer"})
            print(f"  Got {len(tokens)} tokens from Solsniffer")
    except Exception as e:
        print(f"  Solsniffer fetch failed: {e}")

    return tokens


# ------------------------------------------------------------------ #
#  Mock token generator (used when APIs are unavailable)              #
# ------------------------------------------------------------------ #

# 20 real Solana token addresses for realistic mock data
KNOWN_SCAM_ADDRESSES = [
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "Fishy64jCaa3ooqXw7BHtKvYD8BTkSyAPh6RNE3xZpcN",
    "8qJSyQprMC57TWKaYEmetUR3UUiTP2M3hXdcvFB3EfQ8",
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "9nEqaUcb16sQ3Tn1psbkWqyhPdLmfHWjKGqDf4TgrKEy",
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "HZ1JovNiVvGqszpscreQrzHAA2F5kVJFyfbHUFhHMJkF",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
]

KNOWN_SAFE_ADDRESSES = [
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "kinXdEcpDQeHPEuQnqmUgtYykqKTVZek2pqhdqIKkD",
    "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
    "MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey",
    "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT",
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "AGFEad2et2ZJif9jaGpdMixQqvW5i81aBdvKe7PHNfz3",
]


def generate_mock_tokens(count: int) -> list[dict]:
    """Generate deterministic mock tokens when APIs fail."""
    print(f"Generating {count} mock tokens...")
    tokens = []
    half = count // 2

    # Use real addresses first, then generate synthetic ones
    for i in range(half):
        if i < len(KNOWN_SCAM_ADDRESSES):
            addr = KNOWN_SCAM_ADDRESSES[i]
        else:
            seed = hashlib.sha256(f"scam_{i}".encode()).hexdigest()[:44]
            addr = seed
        tokens.append({"address": addr, "label": 1, "source": "mock"})

    for i in range(count - half):
        if i < len(KNOWN_SAFE_ADDRESSES):
            addr = KNOWN_SAFE_ADDRESSES[i]
        else:
            seed = hashlib.sha256(f"safe_{i}".encode()).hexdigest()[:44]
            addr = seed
        tokens.append({"address": addr, "label": 0, "source": "mock"})

    return tokens


# ------------------------------------------------------------------ #
#  Score a single token using all 18 signals                         #
# ------------------------------------------------------------------ #

def score_token(address: str) -> dict:
    """
    Run all 18 signals on a token address.
    Returns a flat dict of signal_id → score.
    """
    from signals.signals import run_all_signals
    from signals.graph_signals import run_graph_signals
    from signals.behavioral_signals import run_behavioral_signals

    scores = {}

    # S01–S09
    for sig in run_all_signals(address):
        key = f"s{sig['signal_id'][1:].zfill(2)}_{sig['signal_id'][1:]}"
        scores[sig["signal_id"]] = sig["score"]

    # S10–S13 (use address as deployer wallet proxy for now)
    for sig in run_graph_signals(address, deployer_wallet=address):
        scores[sig["signal_id"]] = sig["score"]

    # S14–S18
    for sig in run_behavioral_signals(address):
        scores[sig["signal_id"]] = sig["score"]

    return scores


def build_row(token: dict) -> dict | None:
    """Build one CSV row for a token. Returns None on failure."""
    addr  = token["address"]
    label = token["label"]
    source = token["source"]

    try:
        scores = score_token(addr)
        return {
            "token_address":       addr,
            "s01_mint_authority":  scores.get("S01", 0),
            "s02_freeze_authority":scores.get("S02", 0),
            "s03_upgradeable":     scores.get("S03", 0),
            "s04_metadata_mutable":scores.get("S04", 0),
            "s05_lp_lock":         scores.get("S05", 0),
            "s06_deployer_lp":     scores.get("S06", 0),
            "s08_top10_holders":   scores.get("S08", 0),
            "s09_whale_dominance": scores.get("S09", 0),
            "s10_sybil_clusters":  scores.get("S10", 0),
            "s11_rug_history":     scores.get("S11", 0),
            "s12_wallet_age":      scores.get("S12", 0),
            "s13_suspicious_tx":   scores.get("S13", 0),
            "s14_bot_spike":       scores.get("S14", 0),
            "s15_wash_trading":    scores.get("S15", 0),
            "s16_insider_dump":    scores.get("S16", 0),
            "s17_social_verify":   scores.get("S17", 0),
            "s18_fake_engagement": scores.get("S18", 0),
            "label":               label,
            "source":              source,
        }
    except Exception as e:
        print(f"  [SKIP] {addr[:12]}... — {e}")
        return None


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="Scrape and score token dataset")
    parser.add_argument("--mock",  action="store_true", help="Skip real API calls")
    parser.add_argument("--count", type=int, default=500, help="Target token count")
    args = parser.parse_args()

    print(f"\n=== Dataset Scraper ===")
    print(f"Target: {args.count} tokens\n")

    # Collect raw token list
    tokens = []

    if not args.mock:
        tokens += fetch_rugcheck_tokens(limit=args.count // 2)
        time.sleep(1)
        tokens += fetch_solsniffer_tokens(limit=args.count // 2)

    # Fill remaining with mock if APIs didn't return enough
    if len(tokens) < args.count:
        needed = args.count - len(tokens)
        print(f"APIs returned {len(tokens)} tokens — filling {needed} with mock data")
        tokens += generate_mock_tokens(needed)

    # Deduplicate by address
    seen = set()
    unique_tokens = []
    for t in tokens:
        if t["address"] not in seen:
            seen.add(t["address"])
            unique_tokens.append(t)

    print(f"\nScoring {len(unique_tokens)} unique tokens...\n")

    # Score each token and write to CSV
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    rows_written = 0

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

        for i, token in enumerate(unique_tokens, 1):
            row = build_row(token)
            if row:
                writer.writerow(row)
                rows_written += 1
                label_str = "SCAM" if token["label"] == 1 else "SAFE"
                print(f"  [{i:>3}/{len(unique_tokens)}] {token['address'][:16]}...  {label_str}  ({token['source']})")

    print(f"\nDone! {rows_written} tokens saved to {OUTPUT_PATH}")

    # Quick summary
    with open(OUTPUT_PATH) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    scam_count = sum(1 for r in rows if r["label"] == "1")
    safe_count = sum(1 for r in rows if r["label"] == "0")
    print(f"  Scam tokens : {scam_count}")
    print(f"  Safe tokens : {safe_count}")
    print(f"  Total rows  : {len(rows)}")
    print(f"\nNext step: python train_model.py")


if __name__ == "__main__":
    main()
