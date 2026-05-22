"""
behavioral_signals.py — Signals S14–S18

S14 — Bot activity spike detection
S15 — Wash trading detection via Z-score
S16 — Sudden dump pattern from insider wallets
S17 — Twitter/Telegram account verification   (mocked — swap in real API keys later)
S18 — Fake engagement detection via NLP       (mocked — swap in real NLP later)

All signals follow the same output contract as signals.py and graph_signals.py:
{
    "signal_id":     str,
    "token_address": str,
    "score":         float,   # 0.0 – 1.0
    "risk_level":    str,     # LOW | MEDIUM | HIGH | CRITICAL
    "details": {
        "check":       str,
        "result":      any,
        "explanation": str,
    },
    "timestamp": str          # ISO 8601 UTC
}
"""

import hashlib
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import score_to_risk


# ------------------------------------------------------------------ #
#  Shared helpers                                                     #
# ------------------------------------------------------------------ #

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(signal_id, token_address, score, check, result, explanation) -> dict:
    return {
        "signal_id":     signal_id,
        "token_address": token_address,
        "score":         round(float(score), 4),
        "risk_level":    score_to_risk(score),
        "details": {
            "check":       check,
            "result":      result,
            "explanation": explanation,
        },
        "timestamp": _now(),
    }


def _seed(address: str) -> int:
    """Stable pseudo-random seed from any address string."""
    return int(hashlib.sha256(address.encode()).hexdigest(), 16)


# ------------------------------------------------------------------ #
#  Mock data sources (replaced by real API calls when keys exist)     #
# ------------------------------------------------------------------ #

def _mock_transaction_volume(token_address: str) -> list[float]:
    """
    Returns a list of 20 per-minute transaction counts simulating
    launch activity. Real version: pull from Solana RPC or Bitquery.
    """
    seed = _seed(token_address)
    base = (seed % 40) + 5          # baseline txns/min: 5–44
    volumes = []
    for i in range(20):
        # Most minutes are normal; occasionally inject a spike
        if i == 3 or i == 4:        # spike at minute 3-4 (launch pump)
            val = base * ((seed % 8) + 4)
        else:
            val = base + (seed >> i) % 10
        volumes.append(float(val))
    return volumes


def _mock_trade_pairs(token_address: str) -> list[dict]:
    """
    Returns buy/sell pairs per wallet. Real version: Bitquery or on-chain tx parse.
    """
    seed = _seed(token_address)
    pairs = []
    n_wallets = (seed % 8) + 3
    for i in range(n_wallets):
        buys  = (seed >> (i * 2)) % 15 + 1
        sells = (seed >> (i * 3)) % 15 + 1
        pairs.append({
            "wallet": f"Wallet{i}{'x' * 8}{token_address[:4]}",
            "buys":   buys,
            "sells":  sells,
            "ratio":  round(min(buys, sells) / max(buys, sells), 3),
        })
    return pairs


def _mock_insider_wallets(token_address: str) -> list[dict]:
    """
    Wallets that received tokens before public launch (pre-mint recipients).
    Real version: parse token mint tx and earliest transfer recipients.
    """
    seed = _seed(token_address)
    n = (seed % 5) + 1
    wallets = []
    for i in range(n):
        pct_dumped   = round(((seed >> i) % 100) / 100, 3)
        hours_after  = (seed >> (i + 3)) % 48   # hours after launch they sold
        wallets.append({
            "wallet":      f"Insider{i}{token_address[:6]}",
            "pct_dumped":  pct_dumped,
            "hours_after_launch": hours_after,
        })
    return wallets


def _mock_social_data(token_address: str) -> dict:
    """
    Mock Twitter/Telegram data.
    Real version: Twitter API v2 + Telegram Bot API.
    To use real APIs later, replace this function only — nothing else changes.

    How to swap in real data:
        import tweepy
        client = tweepy.Client(bearer_token=os.getenv("TWITTER_BEARER_TOKEN"))
        user = client.get_user(username=handle, user_fields=["created_at","public_metrics"])
        # map fields to the dict below
    """
    seed = _seed(token_address)
    has_twitter  = bool(seed % 3)           # ~66 % have Twitter
    has_telegram = bool(seed % 2)           # 50 % have Telegram
    account_age_days = (seed % 400) + 1     # 1–400 days old
    followers    = (seed % 50000) + 100
    following    = (seed % 5000)  + 10
    return {
        "has_twitter":        has_twitter,
        "has_telegram":       has_telegram,
        "twitter_age_days":   account_age_days if has_twitter  else None,
        "telegram_age_days":  account_age_days if has_telegram else None,
        "followers":          followers if has_twitter else 0,
        "following":          following if has_twitter else 0,
    }


def _mock_engagement_text(token_address: str) -> list[str]:
    """
    Mock recent social posts for NLP analysis.
    Real version: scrape Telegram channel or Twitter timeline.
    """
    seed = _seed(token_address)
    spam_posts = [
        "100x GUARANTEED buy now before it's too late!!!",
        "100x GUARANTEED buy now before it's too late!!!",
        "100x GUARANTEED buy now before it's too late!!!",
        "GEM ALERT this will moon send it send it send it",
        "GEM ALERT this will moon send it send it send it",
    ]
    legit_posts = [
        "New partnership announced — check our roadmap.",
        "Weekly AMA with the dev team this Friday at 3pm UTC.",
        "Audit report published — link in bio.",
        "Community vote on next feature — results tomorrow.",
        "Monthly update: 2k holders, LP locked, audit passed.",
    ]
    # High seed → mostly spam
    if seed % 4 == 0:
        return spam_posts
    elif seed % 4 == 1:
        return legit_posts
    else:
        # Mix
        return spam_posts[:2] + legit_posts[:3]


# ------------------------------------------------------------------ #
#  S14 — Bot Activity Spike Detection                                 #
# ------------------------------------------------------------------ #

def signal_14_bot_activity_spike(token_address: str) -> dict:
    """
    Compares per-minute transaction counts at launch.
    A sudden spike (volume >> baseline) indicates bot wash activity.

    Method: spike ratio = max_volume / median_volume
    Score:
        ratio < 3   → 0.1   normal
        ratio 3–6   → 0.45  suspicious
        ratio 6–10  → 0.7   likely bots
        ratio 10+   → 0.9   almost certainly bots
    """
    volumes = _mock_transaction_volume(token_address)
    sorted_v = sorted(volumes)
    median   = sorted_v[len(sorted_v) // 2]
    peak     = max(volumes)
    ratio    = round(peak / median if median > 0 else 1.0, 2)

    if ratio < 3:
        score = 0.1
    elif ratio < 6:
        score = 0.45
    elif ratio < 10:
        score = 0.7
    else:
        score = 0.9

    explanation = (
        f"Peak txns/min = {peak:.0f}, median = {median:.0f}, spike ratio = {ratio}x. "
        + (
            "Extreme spike — almost certainly bot-driven volume at launch."
            if score >= 0.85 else
            "Large spike detected — likely coordinated bot activity."
            if score >= 0.6 else
            "Moderate spike — worth monitoring but not conclusive."
            if score >= 0.35 else
            "Transaction volume looks organic — no bot spike detected."
        )
    )

    return _build(
        "S14", token_address, score,
        check="bot_activity_spike",
        result={
            "peak_volume":  peak,
            "median_volume": median,
            "spike_ratio":  ratio,
            "volume_series": volumes,
        },
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S15 — Wash Trading Detection via Z-score                           #
# ------------------------------------------------------------------ #

def signal_15_wash_trading(token_address: str) -> dict:
    """
    Identifies wallets that repeatedly buy and sell with near-equal volume.
    Uses Z-score to find statistically abnormal buy/sell symmetry.

    Method:
        For each wallet, compute buy/sell ratio (closer to 1.0 = more symmetric).
        Z-score of the ratio distribution → extreme values = wash trading.
    Score = proportion of wallets with ratio > 0.8 (nearly equal buys and sells).
    """
    pairs = _mock_trade_pairs(token_address)
    if not pairs:
        return _build("S15", token_address, 0.0,
                       "wash_trading_zscore", {}, "No trade data available.")

    ratios = [p["ratio"] for p in pairs]
    mean   = sum(ratios) / len(ratios)
    variance = sum((r - mean) ** 2 for r in ratios) / len(ratios)
    std    = math.sqrt(variance) if variance > 0 else 0.0001

    # Z-scores
    z_scores = [round(abs(r - mean) / std, 3) for r in ratios]

    # Wallets with ratio > 0.8 are near-perfect wash traders
    wash_wallets = [p for p in pairs if p["ratio"] > 0.8]
    wash_pct     = round(len(wash_wallets) / len(pairs), 4)

    score = min(wash_pct * 1.5, 0.95)   # scale up — even 60 % wash is CRITICAL

    explanation = (
        f"{len(wash_wallets)} of {len(pairs)} wallets show near-equal buy/sell "
        f"volume ({wash_pct*100:.0f}% of traders). "
        + (
            "Strong wash trading signal — volume is likely fabricated."
            if score >= 0.7 else
            "Moderate wash trading detected — some volume may be fake."
            if score >= 0.4 else
            "Minimal wash trading — volume appears mostly organic."
        )
    )

    return _build(
        "S15", token_address, score,
        check="wash_trading_zscore",
        result={
            "total_wallets":  len(pairs),
            "wash_wallets":   len(wash_wallets),
            "wash_percent":   wash_pct,
            "mean_ratio":     round(mean, 4),
            "std_ratio":      round(std, 4),
            "z_scores":       z_scores,
        },
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S16 — Sudden Dump Pattern from Insider Wallets                     #
# ------------------------------------------------------------------ #

def signal_16_insider_dump(token_address: str) -> dict:
    """
    Detects wallets that received tokens pre-launch and dumped quickly.

    Score based on:
        - % of allocation dumped
        - How quickly after launch they sold (hours)

    Worst case: dumped 100% within first 6 hours → 0.95
    """
    insiders = _mock_insider_wallets(token_address)
    if not insiders:
        return _build("S16", token_address, 0.0,
                       "insider_dump_pattern", {}, "No insider wallets found.")

    scores = []
    for w in insiders:
        pct   = w["pct_dumped"]
        hours = w["hours_after_launch"]

        # Speed penalty: faster dump = higher risk
        speed_factor = max(0.0, 1.0 - (hours / 48))   # 0h → 1.0, 48h → 0.0
        wallet_score = pct * speed_factor
        scores.append(round(wallet_score, 4))
        w["wallet_score"] = round(wallet_score, 4)

    avg_score = round(sum(scores) / len(scores), 4)
    worst     = max(scores)
    # Final = blend of worst offender and average
    score = round(0.6 * worst + 0.4 * avg_score, 4)

    fast_dumps = [w for w in insiders if w["hours_after_launch"] < 6 and w["pct_dumped"] > 0.5]

    explanation = (
        f"{len(insiders)} insider wallet(s) analyzed. "
        + (
            f"{len(fast_dumps)} dumped >50% of holdings within 6 hours of launch — classic rug pattern."
            if fast_dumps else
            f"Worst insider dumped {max(w['pct_dumped'] for w in insiders)*100:.0f}% "
            f"after {min(w['hours_after_launch'] for w in insiders)}h."
            if score > 0.3 else
            "No aggressive insider selling detected."
        )
    )

    return _build(
        "S16", token_address, score,
        check="insider_dump_pattern",
        result={
            "insider_count": len(insiders),
            "fast_dumps":    len(fast_dumps),
            "avg_score":     avg_score,
            "worst_score":   worst,
            "wallets":       insiders,
        },
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S17 — Twitter/Telegram Account Verification                        #
# ------------------------------------------------------------------ #

def signal_17_social_verification(token_address: str) -> dict:
    """
    Checks existence and age of social media accounts.
    New or missing accounts = higher risk.

    Score:
        No Twitter AND no Telegram → 0.85 (anonymous project)
        Account < 7 days old       → 0.8
        Account < 30 days old      → 0.55
        Account 30–180 days        → 0.3
        Account 180+ days          → 0.1

    NOTE: Currently uses mock data. To enable real data:
        1. Set env vars TWITTER_BEARER_TOKEN and TELEGRAM_BOT_TOKEN
        2. Replace _mock_social_data() with a real API call
        3. Everything else stays the same
    """
    data = _mock_social_data(token_address)

    has_tw = data.get("has_twitter", False)
    has_tg = data.get("has_telegram", False)
    tw_age = data.get("twitter_age_days")
    tg_age = data.get("telegram_age_days")

    if not has_tw and not has_tg:
        score = 0.85
        explanation = "Project has no Twitter or Telegram account — completely anonymous, very high risk."
    else:
        ages = [a for a in [tw_age, tg_age] if a is not None]
        min_age = min(ages) if ages else 0

        if min_age < 7:
            score = 0.8
        elif min_age < 30:
            score = 0.55
        elif min_age < 180:
            score = 0.3
        else:
            score = 0.1

        platforms = []
        if has_tw: platforms.append(f"Twitter ({tw_age}d old)")
        if has_tg: platforms.append(f"Telegram ({tg_age}d old)")
        explanation = (
            f"Social accounts found: {', '.join(platforms)}. "
            + (
                "Account(s) created very recently — likely made just for this launch."
                if min_age < 7 else
                "Accounts under 30 days old — new project with limited track record."
                if min_age < 30 else
                "Accounts have moderate history."
                if min_age < 180 else
                "Established social presence — lower risk."
            )
        )

    return _build(
        "S17", token_address, score,
        check="social_account_verification",
        result=data,
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  S18 — Fake Engagement Detection via NLP                            #
# ------------------------------------------------------------------ #

def signal_18_fake_engagement_nlp(token_address: str) -> dict:
    """
    Analyses recent social posts for bot-like patterns:
        - Repeated identical messages (copy-paste bots)
        - Hype keyword density (moon, 100x, guaranteed, send it)
        - Short message length (bots rarely write full sentences)

    Score = weighted combo of these three sub-scores.

    NOTE: Currently uses mock posts. To enable real NLP:
        1. Pull real posts from Telegram/Twitter
        2. Optionally plug in a Hugging Face model for deeper analysis
        3. Replace _mock_engagement_text() — scoring logic stays the same
    """
    HYPE_WORDS = {
        "moon", "100x", "guaranteed", "gem", "alert",
        "send", "buy", "now", "late", "rocket", "lambo",
    }

    posts = _mock_engagement_text(token_address)
    if not posts:
        return _build("S18", token_address, 0.0,
                       "fake_engagement_nlp", {}, "No social posts found to analyse.")

    # Sub-score 1: Repetition (identical posts = bots)
    unique_ratio = len(set(posts)) / len(posts)      # 1.0 = all unique, 0.0 = all identical
    repetition_score = round(1.0 - unique_ratio, 4)

    # Sub-score 2: Hype keyword density
    hype_counts = []
    for post in posts:
        words = set(post.lower().split())
        hits  = len(words & HYPE_WORDS)
        density = min(hits / max(len(words), 1), 1.0)
        hype_counts.append(density)
    hype_score = round(sum(hype_counts) / len(hype_counts), 4)

    # Sub-score 3: Short message ratio (< 5 words = likely bot)
    short = sum(1 for p in posts if len(p.split()) < 5)
    short_score = round(short / len(posts), 4)

    # Weighted final score
    score = round(0.4 * repetition_score + 0.4 * hype_score + 0.2 * short_score, 4)
    score = min(score, 0.95)

    flags = []
    if repetition_score > 0.4: flags.append("repeated identical messages")
    if hype_score > 0.3:       flags.append("high hype keyword density")
    if short_score > 0.4:      flags.append("many very short posts")

    explanation = (
        f"NLP analysis of {len(posts)} post(s). "
        + (
            f"Flags: {', '.join(flags)}. Engagement appears highly artificial."
            if flags else
            "No fake engagement patterns detected — posts appear organic."
        )
    )

    return _build(
        "S18", token_address, score,
        check="fake_engagement_nlp",
        result={
            "post_count":        len(posts),
            "unique_ratio":      unique_ratio,
            "repetition_score":  repetition_score,
            "hype_score":        hype_score,
            "short_post_score":  short_score,
            "flags":             flags,
        },
        explanation=explanation,
    )


# ------------------------------------------------------------------ #
#  Convenience: run all behavioral signals                            #
# ------------------------------------------------------------------ #

BEHAVIORAL_SIGNALS = [
    signal_14_bot_activity_spike,
    signal_15_wash_trading,
    signal_16_insider_dump,
    signal_17_social_verification,
    signal_18_fake_engagement_nlp,
]


def run_behavioral_signals(token_address: str) -> list[dict]:
    return [fn(token_address) for fn in BEHAVIORAL_SIGNALS]
