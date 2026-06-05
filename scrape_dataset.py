"""
scrape_dataset.py — Generate labeled mock token data and insert into PostgreSQL.

Populates all 4 tables in the correct FK order:
  1. deployer_wallets   (no FK deps)
  2. confirmed_rugs     (no FK deps)
  3. tokens             (FK → deployer_wallets)
  4. signal_results     (FK → tokens)

Also writes data/labeled_tokens.csv for train_model.py.

Usage:
    python3 scrape_dataset.py --count 500
    python3 scrape_dataset.py --count 500 --csv-only   (skip DB, just write CSV)

Requirements:
    pip install psycopg2-binary pandas python-dotenv
"""

import argparse
import csv
import hashlib
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------ #
#  DB config — uses POSTGRES_* from config.py / .env                 #
# ------------------------------------------------------------------ #
from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

DB_CONFIG = {
    "host":     POSTGRES_HOST,
    "port":     POSTGRES_PORT,
    "dbname":   POSTGRES_DB,
    "user":     POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}

BASE      = Path(__file__).parent
DATA_DIR  = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH  = DATA_DIR / "labeled_tokens.csv"

# ------------------------------------------------------------------ #
#  Signal definitions matching SIGNAL_WEIGHTS in scorer.py           #
# ------------------------------------------------------------------ #
SIGNALS = [
    ("S01", "mint_authority",      20),
    ("S02", "freeze_authority",     8),
    ("S03", "upgradeable",         10),
    ("S04", "metadata_mutable",     6),
    ("S05", "lp_not_locked",       18),
    ("S06", "deployer_lp_control", 12),
    ("S07", "liquidity_removal",   15),
    ("S08", "top10_concentration", 10),
    ("S09", "whale_dominance",      8),
    ("S10", "sybil_cluster",       12),
    ("S11", "rug_history",         16),
    ("S12", "wallet_age",           6),
    ("S13", "suspicious_patterns",  8),
    ("S14", "bot_activity",        10),
    ("S15", "wash_trading",         8),
    ("S16", "dump_pattern",        14),
    ("S17", "social_mismatch",      6),
    ("S18", "fake_engagement",      4),
]

TOTAL_WEIGHT = 191

# ------------------------------------------------------------------ #
#  Deterministic helpers (same address → same base values)           #
# ------------------------------------------------------------------ #

def _hash_float(seed: str, salt: str, lo: float = 0.0, hi: float = 1.0) -> float:
    h = int(hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest(), 16)
    return lo + (h % 10000) / 10000 * (hi - lo)


def _rand_address(prefix: str = "") -> str:
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return prefix + "".join(random.choices(chars, k=44 - len(prefix)))


def _rand_date(days_back_min: int, days_back_max: int) -> datetime:
    days = random.randint(days_back_min, days_back_max)
    return datetime.now(timezone.utc) - timedelta(days=days)


# ------------------------------------------------------------------ #
#  Signal score generators                                           #
# ------------------------------------------------------------------ #

def _scam_signal_score(signal_id: str, seed: str) -> float:
    """For scam tokens — high scores (risky) with some variance."""
    base = _hash_float(seed, signal_id, 0.5, 1.0)
    # Certain critical signals are almost always triggered for scams
    if signal_id in ("S01", "S05", "S11", "S16"):
        return round(min(1.0, base + 0.2), 4)
    return round(base, 4)


def _safe_signal_score(signal_id: str, seed: str) -> float:
    """For safe tokens — low scores with some noise."""
    base = _hash_float(seed, signal_id, 0.0, 0.4)
    # Authority signals almost always revoked for safe tokens
    if signal_id in ("S01", "S02"):
        return round(max(0.0, base - 0.3), 4)
    return round(base, 4)


def _compute_final_score(signal_scores: dict) -> int:
    """Mirror of scorer.py compute_score() formula."""
    weighted_sum = sum(
        signal_scores.get(sid, 0.0) * w
        for sid, _, w in SIGNALS
    )
    rule_part = (weighted_sum / TOTAL_WEIGHT) * 100
    # Use rule-based score as ML proxy (no real model at data-gen time)
    ml_prob   = rule_part / 100
    raw       = rule_part + 15 * ml_prob
    return min(100, round(raw))


def _risk_label(score: int) -> str:
    if score >= 70:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    return "LOW"


# ------------------------------------------------------------------ #
#  Generate one token record                                          #
# ------------------------------------------------------------------ #

def generate_token(label: int, index: int) -> dict:
    """
    label: 1 = scam, 0 = safe
    Returns a dict with all fields needed for all 4 tables.
    """
    seed         = f"token_{label}_{index}"
    mint_address = _rand_address("S" if label == 0 else "R")

    # Deployer wallet
    deployer_wallet = _rand_address("D")
    is_flagged      = bool(label == 1 and random.random() > 0.3)
    wallet_age_days = random.randint(1, 10) if label == 1 else random.randint(90, 1000)
    first_seen      = _rand_date(wallet_age_days, wallet_age_days)
    last_seen       = _rand_date(0, 5)

    # Token metadata
    token_names  = ["SafeMoon", "MoonRocket", "SolFloki", "RugToken", "SafeInu",
                    "DiamondHands", "ToTheMoon", "EasyMoney", "TrustCoin", "GemToken"]
    token_name   = random.choice(token_names) + str(index)
    symbol       = token_name[:4].upper()
    created_at   = _rand_date(1, wallet_age_days)

    # Signal scores
    signal_scores = {}
    for sid, _, _ in SIGNALS:
        if label == 1:
            signal_scores[sid] = _scam_signal_score(sid, seed)
        else:
            signal_scores[sid] = _safe_signal_score(sid, seed)

    final_score = _compute_final_score(signal_scores)
    risk_level  = _risk_label(final_score)

    # Rug date (only for scam tokens, ~70% have a recorded rug date)
    rug_date = None
    if label == 1 and random.random() > 0.3:
        rug_date = (_rand_date(1, 30)).date()

    return {
        # deployer_wallets
        "deployer_wallet":  deployer_wallet,
        "first_seen":       first_seen,
        "last_seen":        last_seen,
        "total_tokens":     random.randint(1, 5) if label == 1 else 1,
        "is_flagged":       is_flagged,
        "flag_reason":      "Confirmed rug pull deployer" if is_flagged else None,

        # tokens
        "mint_address":     mint_address,
        "name":             token_name,
        "symbol":           symbol,
        "created_at":       created_at,
        "last_score":       final_score,
        "risk_level":       risk_level,

        # confirmed_rugs (scam only)
        "rug_date":         rug_date,
        "source":           random.choice(["RugCheck", "Solsniffer", "Manual"]) if label == 1 else None,

        # signal_results
        "signal_scores":    signal_scores,

        # ML training label
        "label":            label,

        # CSV columns (flat signal scores)
        **{f"s{sid[1:].zfill(2)}_{name}": score
           for (sid, name, _), score in zip(SIGNALS, signal_scores.values())},
    }


# ------------------------------------------------------------------ #
#  DB insertion                                                       #
# ------------------------------------------------------------------ #

def insert_into_db(records: list[dict], conn) -> None:
    cur = conn.cursor()

    print("\n[DB] Inserting deployer_wallets...")
    deployer_rows = [
        (
            r["deployer_wallet"],
            r["first_seen"],
            r["last_seen"],
            r["total_tokens"],
            r["is_flagged"],
            r["flag_reason"],
        )
        for r in records
    ]
    execute_values(cur, """
        INSERT INTO deployer_wallets
            (wallet_address, first_seen, last_seen, total_tokens, is_flagged, flag_reason)
        VALUES %s
        ON CONFLICT (wallet_address) DO NOTHING
    """, deployer_rows)
    print(f"  → {cur.rowcount} rows inserted (duplicates skipped)")

    print("[DB] Inserting confirmed_rugs...")
    rug_rows = [
        (
            r["deployer_wallet"],
            r["mint_address"],
            r["name"],
            r["rug_date"],
            r["source"],
        )
        for r in records if r["label"] == 1 and r["rug_date"] is not None
    ]
    if rug_rows:
        execute_values(cur, """
            INSERT INTO confirmed_rugs
                (deployer_wallet, token_address, token_name, rug_date, source)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, rug_rows)
        print(f"  → {len(rug_rows)} rug records inserted")

    print("[DB] Inserting tokens...")
    token_rows = [
        (
            r["mint_address"],
            r["deployer_wallet"],
            r["name"],
            r["symbol"],
            r["created_at"],
            r["last_score"],
            r["risk_level"],
        )
        for r in records
    ]
    execute_values(cur, """
        INSERT INTO tokens
            (mint_address, deployer_wallet, name, symbol, created_at, last_score, risk_level)
        VALUES %s
        ON CONFLICT (mint_address) DO NOTHING
    """, token_rows)
    print(f"  → {cur.rowcount} tokens inserted")

    # Fetch inserted token IDs (needed for signal_results FK)
    print("[DB] Fetching token IDs for signal_results...")
    mint_to_id = {}
    cur.execute("SELECT id, mint_address FROM tokens")
    for row in cur.fetchall():
        mint_to_id[row[1]] = row[0]

    print("[DB] Inserting signal_results...")
    sig_rows = []
    for r in records:
        token_id = mint_to_id.get(r["mint_address"])
        if token_id is None:
            continue
        for sid, name, weight in SIGNALS:
            score     = r["signal_scores"][sid]
            triggered = score >= 0.5   # triggered if score above midpoint
            sig_rows.append((
                token_id,
                sid,
                name,
                triggered,
                weight,
            ))

    execute_values(cur, """
        INSERT INTO signal_results
            (token_id, signal_id, signal_name, triggered, weight)
        VALUES %s
    """, sig_rows)
    print(f"  → {len(sig_rows)} signal result rows inserted")

    conn.commit()
    cur.close()
    print("\n[DB] All tables populated successfully. ✅")


# ------------------------------------------------------------------ #
#  Write CSV for train_model.py                                       #
# ------------------------------------------------------------------ #

def write_csv(records: list[dict]) -> None:
    rows = []
    for r in records:
        row = {"mint_address": r["mint_address"], "label": r["label"]}
        for sid, name, _ in SIGNALS:
            col        = f"s{sid[1:].zfill(2)}_{name}"
            row[col]   = r["signal_scores"][sid]
        # Add s07 explicitly with correct column name for train_model.py
        row["s07_liquidity_removal"] = r["signal_scores"].get("S07", 0.0)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False)
    print(f"\n[CSV] Saved {len(df)} rows → {CSV_PATH}")
    print(f"  Scam tokens : {(df['label'] == 1).sum()}")
    print(f"  Safe tokens : {(df['label'] == 0).sum()}")


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="Generate RugShield dataset")
    parser.add_argument("--count",    type=int, default=500,
                        help="Total tokens to generate (half scam, half safe)")
    parser.add_argument("--csv-only", action="store_true",
                        help="Write CSV only, skip database insertion")
    args = parser.parse_args()

    total  = args.count
    half   = total // 2

    print(f"\n=== RugShield Dataset Generator ===")
    print(f"Generating {total} tokens ({half} scam + {half} safe)...\n")

    random.seed(42)   # reproducible

    records = []
    for i in range(half):
        records.append(generate_token(label=1, index=i))   # scam
    for i in range(half):
        records.append(generate_token(label=0, index=i))   # safe

    random.shuffle(records)

    # Always write CSV
    write_csv(records)

    if args.csv_only:
        print("\n[--csv-only mode] Skipping database insertion.")
        print("Next step: python3 train_model.py")
        return

    # Connect and insert into DB
    print(f"\n[DB] Connecting to PostgreSQL...")
    print(f"  Host   : {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  DB     : {DB_CONFIG['dbname']}")
    print(f"  User   : {DB_CONFIG['user']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("  Connection: ✅\n")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to PostgreSQL: {e}")
        print("\nFix: create a .env file in this folder (see env.example) with:")
        print("  POSTGRES_HOST=localhost")
        print("  POSTGRES_DB=rugshield")
        print("  POSTGRES_USER=rugshield")
        print("  POSTGRES_PASSWORD=change_me")
        print("\nOr run with --csv-only to skip the DB step.")
        sys.exit(1)

    try:
        insert_into_db(records, conn)
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] DB insertion failed: {e}")
        print("The CSV was still saved. Fix the DB error and re-run.")
        sys.exit(1)
    finally:
        conn.close()

    print(f"\nNext steps:")
    print(f"  1. python3 train_model.py   ← retrain ML model")
    print(f"  2. python3 scorer.py <any_token_address>   ← test scorer")


if __name__ == "__main__":
    main()
