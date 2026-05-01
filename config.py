"""
Shared configuration and utilities for p2-scoring pipeline.
"""

import os

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_QUEUE_KEY = "token_events"

# Solana RPC
SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.mainnet-beta.solana.com"
)

# Risk thresholds
SCORE_THRESHOLDS = {
    "LOW":      (0.0, 0.3),
    "MEDIUM":   (0.3, 0.6),
    "HIGH":     (0.6, 0.8),
    "CRITICAL": (0.8, 1.0),
}

def score_to_risk(score: float) -> str:
    """Convert a numeric score (0–1) to a risk label."""
    for level, (lo, hi) in SCORE_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "CRITICAL"  # score == 1.0 edge case
