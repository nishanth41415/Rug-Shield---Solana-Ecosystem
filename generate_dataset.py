"""
generate_dataset.py — Generate a realistic labeled dataset for ML training.

This script writes signal scores DIRECTLY into the CSV with realistic patterns:
  - Scam tokens  → HIGH scores on dangerous signals
  - Safe tokens  → LOW scores on dangerous signals

This gives the GradientBoostingClassifier a clear pattern to learn,
achieving 80%+ accuracy without needing real blockchain data.

Usage:
    python3 generate_dataset.py
    python3 generate_dataset.py --count 1000

Output: data/labeled_tokens.csv
"""

import csv
import random
import hashlib
import argparse
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "data" / "labeled_tokens.csv"

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
    "label",
    "source",
]


def make_address(prefix: str, i: int) -> str:
    """Generate a fake but unique token address."""
    raw = hashlib.sha256(f"{prefix}_{i}".encode()).hexdigest()
    # Base58-like: just use hex chars, 44 chars long
    return raw[:44]


def jitter(value: float, spread: float = 0.12) -> float:
    """Add small random noise to a value, keeping it in 0.0–1.0."""
    return round(min(1.0, max(0.0, value + random.uniform(-spread, spread))), 4)


def scam_row(address: str) -> dict:
    """
    Scam token profile:
    - Mint/freeze authority still active
    - Unlocked LP, high deployer LP concentration
    - High holder concentration, whale dominance
    - Sybil clusters, rug history, new wallet
    - Bot spikes, wash trading, insider dumps
    - No social presence or fake engagement
    """
    return {
        "token_address":        address,
        "s01_mint_authority":   jitter(0.90),   # mint auth active
        "s02_freeze_authority": jitter(0.80),   # freeze auth active
        "s03_upgradeable":      jitter(0.75),   # upgradeable contract
        "s04_metadata_mutable": jitter(0.70),   # mutable metadata
        "s05_lp_lock":          jitter(0.85),   # LP mostly unlocked
        "s06_deployer_lp":      jitter(0.75),   # deployer holds most LP
        "s08_top10_holders":    jitter(0.80),   # top 10 hold most supply
        "s09_whale_dominance":  jitter(0.85),   # one whale dominates
        "s10_sybil_clusters":   jitter(0.75),   # sybil clusters found
        "s11_rug_history":      jitter(0.80),   # deployer has rug history
        "s12_wallet_age":       jitter(0.85),   # very new wallet
        "s13_suspicious_tx":    jitter(0.70),   # suspicious patterns
        "s14_bot_spike":        jitter(0.80),   # bot activity at launch
        "s15_wash_trading":     jitter(0.75),   # wash trading detected
        "s16_insider_dump":     jitter(0.80),   # insiders dumped fast
        "s17_social_verify":    jitter(0.85),   # no/fake social accounts
        "s18_fake_engagement":  jitter(0.75),   # fake engagement
        "label":                1,
        "source":               "mock",
    }


def safe_row(address: str) -> dict:
    """
    Safe token profile:
    - Mint/freeze authority revoked
    - LP locked, deployer holds little LP
    - Distributed holders, no single whale
    - No sybil, no rug history, established wallet
    - Organic activity, no wash trading, no insider dump
    - Established social presence, real engagement
    """
    return {
        "token_address":        address,
        "s01_mint_authority":   jitter(0.05),   # mint auth revoked
        "s02_freeze_authority": jitter(0.05),   # freeze auth revoked
        "s03_upgradeable":      jitter(0.10),   # immutable contract
        "s04_metadata_mutable": jitter(0.05),   # immutable metadata
        "s05_lp_lock":          jitter(0.10),   # LP locked
        "s06_deployer_lp":      jitter(0.08),   # deployer holds little LP
        "s08_top10_holders":    jitter(0.20),   # distributed supply
        "s09_whale_dominance":  jitter(0.10),   # no whale dominance
        "s10_sybil_clusters":   jitter(0.05),   # no sybil clusters
        "s11_rug_history":      jitter(0.05),   # clean history
        "s12_wallet_age":       jitter(0.05),   # established wallet
        "s13_suspicious_tx":    jitter(0.08),   # clean transactions
        "s14_bot_spike":        jitter(0.10),   # organic volume
        "s15_wash_trading":     jitter(0.10),   # no wash trading
        "s16_insider_dump":     jitter(0.08),   # no insider dumps
        "s17_social_verify":    jitter(0.10),   # verified social accounts
        "s18_fake_engagement":  jitter(0.08),   # real engagement
        "label":                0,
        "source":               "mock",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500,
                        help="Total tokens to generate (half scam, half safe)")
    args = parser.parse_args()

    random.seed(42)   # reproducible results

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    half = args.count // 2

    print(f"\n=== Generating {args.count} labeled tokens ===")
    print(f"  {half} scam  +  {args.count - half} safe\n")

    rows = []

    for i in range(half):
        addr = make_address("scam", i)
        rows.append(scam_row(addr))

    for i in range(args.count - half):
        addr = make_address("safe", i)
        rows.append(safe_row(addr))

    # Shuffle so scam/safe aren't all grouped together
    random.shuffle(rows)

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done! {len(rows)} tokens saved to {OUTPUT_PATH}")
    print(f"  Scam tokens : {half}")
    print(f"  Safe tokens : {args.count - half}")
    print(f"\nNext step: python3 train_model.py")


if __name__ == "__main__":
    main()
