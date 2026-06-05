"""
config.py — Shared configuration for the RugShield P2 scoring pipeline.

All environment variables can be overridden via a .env file or shell exports.
See .env.example for the full list of variables.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
#  Solana RPC (HTTP + WebSocket)
# ---------------------------------------------------------------------------

# Premium RPC (Helius / QuickNode / Triton) — set SOLANA_RPC_URL in .env for production.
SOLANA_RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.mainnet-beta.solana.com",
)

# WebSocket RPC for solana_listener.py — set SOLANA_WSS_URL in .env (no public default).
SOLANA_WSS_URL = os.getenv("SOLANA_WSS_URL", "")

# ---------------------------------------------------------------------------
#  Redis
# ---------------------------------------------------------------------------

REDIS_HOST      = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT      = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB        = int(os.getenv("REDIS_DB", 0))
REDIS_QUEUE_KEY = "token_events"

# ---------------------------------------------------------------------------
#  PostgreSQL (P1 rug-history database)
# ---------------------------------------------------------------------------

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.getenv("POSTGRES_USER", "rugshield")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "rugshield")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# ---------------------------------------------------------------------------
#  Social APIs — OPTIONAL (S17/S18 are UNAVAILABLE without these)
# ---------------------------------------------------------------------------

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ---------------------------------------------------------------------------
#  External APIs (no key required)
# ---------------------------------------------------------------------------

# DexScreener — free public API, no API key needed
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"

# ---------------------------------------------------------------------------
#  Solana Program IDs
# ---------------------------------------------------------------------------

# Metaplex Token Metadata program — used for S04 (metadata mutability)
METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"

# SPL Token program — used for holder / mint account queries
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

# BPF Upgradeable Loader — used for S03 (upgradeable contract check)
BPF_UPGRADEABLE_LOADER_ID = "BPFLoaderUpgradeab1e11111111111111111111111"

# ---------------------------------------------------------------------------
#  Risk score thresholds  (raw 0.0–1.0 signal scores)
# ---------------------------------------------------------------------------

SCORE_THRESHOLDS = {
    "LOW":      (0.0, 0.3),
    "MEDIUM":   (0.3, 0.6),
    "HIGH":     (0.6, 0.8),
    "CRITICAL": (0.8, 1.01),   # upper bound > 1 catches score == 1.0
}


def score_to_risk(score: float) -> str:
    """Convert a raw signal score (0.0–1.0) to a human-readable risk label."""
    for level, (lo, hi) in SCORE_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "CRITICAL"


# ---------------------------------------------------------------------------
#  Verified major tokens — reduces false-positive risk only (not a bypass)
# ---------------------------------------------------------------------------

VERIFIED_TOKENS: dict[str, dict] = {
    # Circle USDC (Solana mainnet)
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {
        "symbol": "USDC",
        "type": "stablecoin",
        "max_risk_score": 25,
    },
    # Tether USDT (Solana)
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": {
        "symbol": "USDT",
        "type": "stablecoin",
        "max_risk_score": 25,
    },
    # Wrapped SOL
    "So11111111111111111111111111111111111111112": {
        "symbol": "wSOL",
        "type": "native_wrapped",
        "max_risk_score": 20,
    },
}


def is_verified_token(mint_address: str) -> bool:
    return mint_address in VERIFIED_TOKENS


def get_verified_token_profile(mint_address: str) -> dict | None:
    return VERIFIED_TOKENS.get(mint_address)


def warn_if_missing_env() -> None:
    """Print non-fatal warnings when optional production env vars are unset."""
    if SOLANA_RPC_URL == "https://api.mainnet-beta.solana.com":
        print(
            "[WARN] Using public Solana RPC — rate limits may apply. "
            "Set SOLANA_RPC_URL in .env for production."
        )
