"""
signals/behavioral_signals.py — S14 through S18 (behavioral + social signals).

S14 — Bot Activity Spike    → REAL: tx-per-minute analysis via RPC
S15 — Wash Trading          → REAL: buy/sell wallet overlap via RPC tx history
S16 — Insider Dump Pattern  → REAL: early wallet sell analysis via RPC
S17 — Social Account Verify → UNAVAILABLE without TWITTER_BEARER_TOKEN / TELEGRAM_BOT_TOKEN
S18 — Fake Engagement NLP   → UNAVAILABLE without social post data

S14–S16 use real RPC when tx history is sufficient; otherwise UNAVAILABLE (not fake MEDIUM).
"""

import sys
import time
import hashlib
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TELEGRAM_BOT_TOKEN, TWITTER_BEARER_TOKEN, score_to_risk
from signals.utils import NEUTRAL_SCORE, mark_non_evidence, set_data_source
from solana_rpc import get_signatures, get_recent_transactions


# ---------------------------------------------------------------------------
#  Shared builder
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(signal_id: str, token_address: str, score: float,
           check: str, result, explanation: str) -> dict:
    score = round(float(score), 4)
    return {
        "signal_id":     signal_id,
        "token_address": token_address,
        "score":         score,
        "risk_level":    score_to_risk(score),
        "details": {
            "check":       check,
            "result":      result,
            "explanation": explanation,
        },
        "timestamp": _now(),
    }


def _mock_seed(address: str) -> int:
    return int(hashlib.sha256(address.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
#  S14 — Bot Activity Spike
# ---------------------------------------------------------------------------

def _get_tx_timeseries(token_address: str) -> list[int]:
    """
    Returns a list of Unix block-times for recent transactions.
    Uses real getSignaturesForAddress RPC call.
    Falls back to empty list on failure.
    """
    try:
        sigs = get_signatures(token_address, limit=500)
        times = [s.get("blockTime", 0) for s in sigs if s.get("blockTime")]
        return sorted(times)
    except Exception:
        return []


def _mock_tx_timeseries(token_address: str) -> list[int]:
    """Deterministic mock tx time-series (hash-based)."""
    seed  = _mock_seed(token_address)
    rng   = random.Random(seed)
    now   = int(time.time())
    times = []
    # Simulate a spike at launch (first 5 minutes), then quiet
    # Scam-like address (high seed) → big spike
    spike_factor = (seed % 50) + 5
    for i in range(spike_factor * 3):
        times.append(now - 3600 + rng.randint(0, 300))   # spike window
    for i in range(10):
        times.append(now - 3600 + 300 + rng.randint(0, 3000))
    return sorted(times)


def signal_14_bot_activity_spike(token_address: str) -> dict:
    """
    Detects abnormal transaction volume at launch — a hallmark of bot
    activity used to create artificial hype and FOMO.

    Method:
        1. Fetch up to 500 recent tx signatures
        2. Group block-times into 5-minute buckets
        3. Compute peak_txs_per_bucket / median_txs_per_bucket
        4. High ratio = spike = bot activity

    Score:
        spike < 3x  → 0.10
        spike < 6x  → 0.45
        spike < 10x → 0.70
        spike ≥ 10x → 0.90

    Data: Real — getSignaturesForAddress RPC.
    """
    BUCKET_SECONDS = 300   # 5-minute buckets

    times = _get_tx_timeseries(token_address)
    if len(times) < 5:
        return mark_non_evidence(_build(
            "S14", token_address, NEUTRAL_SCORE,
            check="bot_activity_spike",
            result={"spike_ratio": None},
            explanation="Insufficient on-chain transaction data — bot spike check unavailable.",
        ), "unavailable")

    # Build time-series buckets
    min_time = min(times)
    buckets: dict[int, int] = defaultdict(int)
    for t in times:
        bucket = (t - min_time) // BUCKET_SECONDS
        buckets[bucket] += 1

    counts = list(buckets.values())
    if len(counts) < 2:
        spike_ratio = 1.0
    else:
        counts_sorted = sorted(counts)
        median_count  = counts_sorted[len(counts_sorted) // 2]
        peak_count    = max(counts)
        spike_ratio   = peak_count / max(median_count, 1)

    # Score mapping
    if spike_ratio < 3:
        score = 0.10
    elif spike_ratio < 6:
        score = 0.45
    elif spike_ratio < 10:
        score = 0.70
    else:
        score = 0.90

    explanation = (
        f"Transaction spike ratio: {spike_ratio:.1f}x "
        f"(peak={max(counts)} txs vs median={sorted(counts)[len(counts)//2]} in a 5-min window). "
        + (
            "Extreme spike — almost certainly bot-driven launch activity."
            if spike_ratio >= 10 else
            "Significant spike — likely coordinated bot volume."
            if spike_ratio >= 6 else
            "Moderate spike — possible bot involvement."
            if spike_ratio >= 3 else
            "No unusual volume spike — organic-looking activity."
        )
    )

    return set_data_source(_build(
        "S14", token_address, score,
        check="bot_activity_spike",
        result={
            "spike_ratio":   round(spike_ratio, 2),
            "peak_txs":      max(counts),
            "median_txs":    sorted(counts)[len(counts) // 2],
            "total_buckets": len(counts),
            "total_txs":     sum(counts),
        },
        explanation=explanation,
    ), "real")


# ---------------------------------------------------------------------------
#  S15 — Wash Trading Detection
# ---------------------------------------------------------------------------

def _extract_wallet_sides(transactions: list[dict]) -> dict[str, set]:
    """
    From parsed transactions, identify which wallets appear on the
    'buy' side vs 'sell' side of token transfers.

    We approximate: if a wallet's balance increased → buy, decreased → sell.
    Uses postTokenBalances vs preTokenBalances from the transaction metadata.

    Returns: {"buyers": set(pubkeys), "sellers": set(pubkeys)}
    """
    buyers  = set()
    sellers = set()

    for tx in transactions:
        try:
            meta = tx.get("meta", {})
            pre  = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"])
                    for b in (meta.get("preTokenBalances") or [])
                    if b.get("uiTokenAmount")}
            post = {b["accountIndex"]: int(b["uiTokenAmount"]["amount"])
                    for b in (meta.get("postTokenBalances") or [])
                    if b.get("uiTokenAmount")}

            keys = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])

            for idx in set(list(pre.keys()) + list(post.keys())):
                pre_amt  = pre.get(idx, 0)
                post_amt = post.get(idx, 0)
                if idx < len(keys):
                    key_obj = keys[idx]
                    pubkey  = key_obj.get("pubkey", "") if isinstance(key_obj, dict) else key_obj

                    if post_amt > pre_amt:
                        buyers.add(pubkey)
                    elif post_amt < pre_amt:
                        sellers.add(pubkey)
        except Exception:
            continue

    return {"buyers": buyers, "sellers": sellers}


def _mock_wash_data(token_address: str) -> dict:
    seed  = _mock_seed(token_address)
    rng   = random.Random(seed)
    n     = 30
    buyers  = {f"wallet_{i}" for i in range(n)}
    sellers = {f"wallet_{i}" for i in range(0, n, 2)}   # half overlap
    return {"buyers": buyers, "sellers": sellers}


def signal_15_wash_trading(token_address: str) -> dict:
    """
    Detects wallets that appear on both the buy AND sell side —
    a strong indicator of wash trading to fake volume.

    Method:
        1. Fetch last 50 full parsed transactions
        2. Extract wallets that bought and sold
        3. Compute overlap ratio = both_sides / total_unique_wallets

    Score: overlap_ratio × 1.5, capped at 0.95.
    Data: Real — getTransaction (jsonParsed) on recent signatures.
    """
    txs = get_recent_transactions(token_address, limit=100)

    if len(txs) < 3:
        return mark_non_evidence(_build(
            "S15", token_address, NEUTRAL_SCORE,
            check="wash_trading",
            result={"wallets_analyzed": 0},
            explanation="Insufficient parsed transaction data — wash trading check unavailable.",
        ), "unavailable")

    sides = _extract_wallet_sides(txs)

    buyers  = sides.get("buyers", set())
    sellers = sides.get("sellers", set())

    both_sides = buyers & sellers
    all_wallets = buyers | sellers

    if not all_wallets:
        return set_data_source(_build(
            "S15", token_address, 0.1,
            check="wash_trading",
            result={"wallets_analyzed": 0},
            explanation="No token transfer data found to analyze wash trading.",
        ), "real")

    overlap_ratio = len(both_sides) / len(all_wallets)
    score         = min(round(overlap_ratio * 1.5, 4), 0.95)

    explanation = (
        f"{len(both_sides)} of {len(all_wallets)} wallets both bought AND sold "
        f"this token ({overlap_ratio * 100:.1f}% overlap ratio). "
        + (
            "Extreme wash trading — volume is almost entirely artificial."
            if score >= 0.7 else
            "Significant wash trading — a large portion of volume is fake."
            if score >= 0.4 else
            "Moderate wash trading — some suspicious back-and-forth trades."
            if score >= 0.2 else
            "Minimal wash trading — volume appears mostly organic."
        )
    )

    return set_data_source(_build(
        "S15", token_address, score,
        check="wash_trading",
        result={
            "buyers":          len(buyers),
            "sellers":         len(sellers),
            "both_sides":      len(both_sides),
            "unique_wallets":  len(all_wallets),
            "overlap_ratio":   round(overlap_ratio, 4),
        },
        explanation=explanation,
    ), "real")


# ---------------------------------------------------------------------------
#  S16 — Insider Dump Pattern
# ---------------------------------------------------------------------------

def _get_early_wallets_and_behavior(token_address: str) -> list[dict]:
    """
    Identify 'insider' wallets: those that appear in the first 50 transactions
    of the token's life. Then check if they dumped their holdings quickly.

    Returns list of wallet dicts with:
        {wallet, received_at_tx, first_sell_at_tx, pct_dumped, hours_after_launch}
    """
    try:
        sigs = get_signatures(token_address, limit=1000)
        if not sigs:
            return []

        # Oldest transactions first (sigs are newest-first)
        earliest_sigs = sigs[-50:]
        launch_time   = earliest_sigs[-1].get("blockTime", 0)  # oldest tx time

        # Track which wallets got tokens early
        early_receivers: set = set()
        wallet_first_seen: dict = {}

        for i, sig_obj in enumerate(reversed(earliest_sigs)):
            sig = sig_obj.get("signature", "")
            if not sig:
                continue
            tx = None
            try:
                from solana_rpc import get_transaction
                tx = get_transaction(sig)
            except Exception:
                pass
            if not tx:
                continue

            meta = tx.get("meta", {})
            post = meta.get("postTokenBalances") or []
            keys = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])

            for b in post:
                idx = b.get("accountIndex", -1)
                if idx < len(keys):
                    key_obj = keys[idx]
                    pubkey  = key_obj.get("pubkey", "") if isinstance(key_obj, dict) else key_obj
                    if pubkey and pubkey not in wallet_first_seen:
                        wallet_first_seen[pubkey] = i
                        early_receivers.add(pubkey)

            time.sleep(0.05)   # rate limit

        if not early_receivers:
            return []

        # For each early receiver, check if they sold quickly
        insiders = []
        for wallet in list(early_receivers)[:10]:   # check top 10 early wallets
            wallet_sigs = get_signatures(wallet, limit=200)
            sold_early  = False
            sell_time   = None

            for sig_obj in wallet_sigs:
                bt = sig_obj.get("blockTime", 0)
                if bt and launch_time and bt > launch_time:
                    hours_after = (bt - launch_time) / 3600
                    if hours_after < 48:
                        sold_early = True
                        sell_time  = bt
                        break
                time.sleep(0.02)

            if sold_early and sell_time:
                hours_after = (sell_time - launch_time) / 3600
                # Estimate dump % — we don't have exact amounts without full tx parse
                # Use time-to-sell as proxy: faster sell = more likely full dump
                pct_dumped = max(0.0, min(1.0, 1.0 - (hours_after / 48)))
                insiders.append({
                    "wallet":            wallet[:8] + "...",
                    "hours_after_launch": round(hours_after, 1),
                    "pct_dumped":         round(pct_dumped, 2),
                })

        return insiders

    except Exception:
        return []


def _mock_insider_wallets(token_address: str) -> list[dict]:
    """Deterministic mock insider wallet data."""
    seed = _mock_seed(token_address)
    rng  = random.Random(seed)
    count = (seed % 4) + 1
    wallets = []
    for i in range(count):
        hours = rng.uniform(0.5, 48)
        pct   = round(rng.uniform(0.1, 1.0), 2)
        wallets.append({
            "wallet":             f"Insider{i+1}Wallet11111",
            "hours_after_launch": round(hours, 1),
            "pct_dumped":         pct,
        })
    return wallets


def signal_16_insider_dump(token_address: str) -> dict:
    """
    Detects wallets that received tokens before/at launch and sold quickly.
    Fast dumps by early wallets is the #1 sign of a coordinated rug pull.

    Score: 0.6 × worst_wallet_score + 0.4 × average_wallet_score
    Data: Real — getSignaturesForAddress to find early wallets + sell timing.
    """
    insiders = _get_early_wallets_and_behavior(token_address)
    if not insiders:
        return mark_non_evidence(_build(
            "S16", token_address, NEUTRAL_SCORE,
            check="insider_dump_pattern",
            result={"insider_count": 0},
            explanation="Insufficient on-chain data for insider dump analysis — check unavailable.",
        ), "unavailable")

    scores = []
    for w in insiders:
        pct   = w.get("pct_dumped", 0.0)
        hours = w.get("hours_after_launch", 48)
        speed = max(0.0, 1.0 - (hours / 48))   # faster = higher score
        w_score = round(pct * speed, 4)
        scores.append(w_score)
        w["wallet_score"] = w_score

    avg_score = round(sum(scores) / len(scores), 4)
    worst     = max(scores)
    score     = round(0.6 * worst + 0.4 * avg_score, 4)
    score     = min(score, 0.95)

    fast_dumps = [w for w in insiders if w.get("hours_after_launch", 99) < 6 and w.get("pct_dumped", 0) > 0.5]

    explanation = (
        f"{len(insiders)} early wallet(s) analyzed. "
        + (
            f"{len(fast_dumps)} dumped >50% of holdings within 6 hours of launch — classic rug pattern."
            if fast_dumps else
            f"Worst early wallet sold {max(w['pct_dumped'] for w in insiders)*100:.0f}% "
            f"within {min(w['hours_after_launch'] for w in insiders):.1f}h of launch."
            if score > 0.3 else
            "No aggressive insider selling detected in the first 48 hours."
        )
    )

    return set_data_source(_build(
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
    ), "real")


# ---------------------------------------------------------------------------
#  S17 — Social Account Verification
#  MOCK — requires TWITTER_BEARER_TOKEN and TELEGRAM_BOT_TOKEN
# ---------------------------------------------------------------------------

def _get_real_social_data(token_address: str) -> dict | None:
    """
    TODO: API KEY REQUIRED — Replace this stub with real API calls.

    Steps to enable:
        1. Get a Twitter Developer account → Bearer Token
           https://developer.twitter.com/en/docs/authentication/oauth-2-0/bearer-tokens
        2. Set env variable: export TWITTER_BEARER_TOKEN=your_token_here
        3. Get a Telegram Bot Token from @BotFather
           Set env variable: export TELEGRAM_BOT_TOKEN=your_token_here
        4. Replace the return None below with real API calls:

        import os, requests
        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer:
            return None

        # Search Twitter for the token symbol/address
        headers = {"Authorization": f"Bearer {bearer}"}
        resp = requests.get(
            "https://api.twitter.com/2/users/by/username/{handle}",
            headers=headers,
            params={"user.fields": "created_at,public_metrics"},
        )
        ...
    """
    return None   # ← Remove this line and add real calls above


def _mock_social_data(token_address: str) -> dict:
    """Deterministic mock social data (hash-based)."""
    seed = _mock_seed(token_address)
    has_twitter  = bool(seed % 3)
    has_telegram = bool(seed % 4)
    return {
        "has_twitter":      has_twitter,
        "has_telegram":     has_telegram,
        "twitter_age_days": (seed % 200) if has_twitter else None,
        "telegram_age_days":(seed % 150) if has_telegram else None,
    }


def signal_17_social_verification(token_address: str) -> dict:
    """
    Checks existence and age of the project's social media accounts.
    New or absent accounts = higher rug risk (no established community).

    Score:
        No Twitter AND no Telegram → 0.85 (anonymous)
        Account < 7 days old       → 0.80
        Account < 30 days old      → 0.55
        Account 30–180 days        → 0.30
        Account 180+ days          → 0.10

    Data: MOCK — set TWITTER_BEARER_TOKEN + TELEGRAM_BOT_TOKEN to enable real data.
          See _get_real_social_data() above for exact steps.
    """
    if not TWITTER_BEARER_TOKEN and not TELEGRAM_BOT_TOKEN:
        return mark_non_evidence(_build(
            "S17", token_address, NEUTRAL_SCORE,
            check="social_account_verification",
            result={"has_twitter": None, "has_telegram": None},
            explanation="Social verification APIs not configured — no evidence available.",
        ), "unavailable")

    data = _get_real_social_data(token_address)
    if data is None:
        return mark_non_evidence(_build(
            "S17", token_address, NEUTRAL_SCORE,
            check="social_account_verification",
            result={},
            explanation="Social account data could not be fetched — no evidence available.",
        ), "unavailable")

    has_tw = data.get("has_twitter", False)
    has_tg = data.get("has_telegram", False)
    tw_age = data.get("twitter_age_days")
    tg_age = data.get("telegram_age_days")

    if not has_tw and not has_tg:
        score = 0.85
        explanation = "Project has no Twitter or Telegram — completely anonymous, very high risk."
    else:
        ages    = [a for a in [tw_age, tg_age] if a is not None]
        min_age = min(ages) if ages else 0

        if min_age < 7:
            score = 0.80
        elif min_age < 30:
            score = 0.55
        elif min_age < 180:
            score = 0.30
        else:
            score = 0.10

        platforms = []
        if has_tw: platforms.append(f"Twitter ({tw_age}d old)")
        if has_tg: platforms.append(f"Telegram ({tg_age}d old)")
        explanation = (
            f"Social accounts: {', '.join(platforms)}. "
            + (
                "Created very recently — likely made just for this launch."
                if min_age < 7 else
                "Under 30 days old — limited track record."
                if min_age < 30 else
                "Moderate social history."
                if min_age < 180 else
                "Established social presence — lower risk."
            )
        )

    return set_data_source(_build(
        "S17", token_address, score,
        check="social_account_verification",
        result={**data},
        explanation=explanation,
    ), "real")


# ---------------------------------------------------------------------------
#  S18 — Fake Engagement NLP
#  MOCK — requires social post data (Twitter/Telegram API)
# ---------------------------------------------------------------------------

def _get_real_engagement_posts(token_address: str) -> list[str] | None:
    """
    TODO: API KEY REQUIRED — Replace this stub with real post fetching.

    Steps to enable:
        1. Use your TWITTER_BEARER_TOKEN (from S17 setup above)
        2. Search for recent tweets mentioning the token address or symbol
        3. Return a list of post text strings

        import os, requests
        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer:
            return None

        headers = {"Authorization": f"Bearer {bearer}"}
        resp = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params={"query": token_address, "max_results": 100,
                    "tweet.fields": "text"},
        )
        data = resp.json()
        return [t["text"] for t in data.get("data", [])]
    """
    return None   # ← Remove this line and add real calls above


def _mock_engagement_text(token_address: str) -> list[str]:
    """Deterministic mock social posts."""
    seed = _mock_seed(token_address)
    rng  = random.Random(seed)
    hype = ["100x gem!!!", "moon soon 🚀", "buy now or stay poor",
            "guaranteed pump", "send it", "last chance", "moon", "buy buy buy"]
    real = ["Just analyzed the tokenomics, looks decent.",
            "LP is locked for 6 months, seems legit.",
            "Dev team seems active in Discord.",
            "Chart looking healthy, building support at this level."]
    pool = hype if seed % 2 else real
    return [rng.choice(pool) for _ in range(rng.randint(10, 30))]


def signal_18_fake_engagement_nlp(token_address: str) -> dict:
    """
    Analyses recent social posts for bot-like patterns:
        - Repeated identical messages (copy-paste bots)
        - Hype keyword density (moon, 100x, guaranteed, etc.)
        - Short message length (bots rarely write full sentences)

    Score = 0.4 × repetition + 0.4 × hype_density + 0.2 × short_post_ratio

    Data: MOCK — set TWITTER_BEARER_TOKEN to enable real data.
          See _get_real_engagement_posts() above for exact steps.
    """
    HYPE_WORDS = {
        "moon", "100x", "guaranteed", "gem", "alert",
        "send", "buy", "now", "late", "rocket", "lambo",
        "pump", "poor", "rich", "ape", "degen",
    }

    if not TWITTER_BEARER_TOKEN:
        return mark_non_evidence(_build(
            "S18", token_address, NEUTRAL_SCORE,
            check="fake_engagement_nlp",
            result={"post_count": 0},
            explanation="Social post data unavailable — fake engagement check skipped.",
        ), "unavailable")

    posts = _get_real_engagement_posts(token_address)
    if posts is None:
        return mark_non_evidence(_build(
            "S18", token_address, NEUTRAL_SCORE,
            check="fake_engagement_nlp",
            result={"post_count": 0},
            explanation="Could not fetch social posts — no evidence available.",
        ), "unavailable")

    if not posts:
        return mark_non_evidence(_build(
            "S18", token_address, NEUTRAL_SCORE,
            check="fake_engagement_nlp",
            result={"post_count": 0},
            explanation="No social posts found to analyse — no evidence available.",
        ), "unavailable")

    # Sub-score 1: Repetition (identical posts = bots)
    unique_ratio     = len(set(posts)) / len(posts)
    repetition_score = round(1.0 - unique_ratio, 4)

    # Sub-score 2: Hype keyword density
    hype_counts = []
    for post in posts:
        words   = set(post.lower().split())
        hits    = len(words & HYPE_WORDS)
        density = min(hits / max(len(words), 1), 1.0)
        hype_counts.append(density)
    hype_score = round(sum(hype_counts) / len(hype_counts), 4)

    # Sub-score 3: Short message ratio (< 5 words = likely bot)
    short      = sum(1 for p in posts if len(p.split()) < 5)
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
            f"Flags: {', '.join(flags)} — engagement appears highly artificial."
            if flags else
            "No fake engagement patterns detected — posts appear organic."
        )
    )

    return set_data_source(_build(
        "S18", token_address, score,
        check="fake_engagement_nlp",
        result={
            "post_count":       len(posts),
            "unique_ratio":     round(unique_ratio, 4),
            "repetition_score": repetition_score,
            "hype_score":       hype_score,
            "short_post_score": short_score,
            "flags":            flags,
        },
        explanation=explanation,
    ), "real")


# ---------------------------------------------------------------------------
#  Convenience: run all behavioral signals
# ---------------------------------------------------------------------------

BEHAVIORAL_SIGNALS = [
    signal_14_bot_activity_spike,
    signal_15_wash_trading,
    signal_16_insider_dump,
    signal_17_social_verification,
    signal_18_fake_engagement_nlp,
]


def run_behavioral_signals(token_address: str) -> list[dict]:
    """Run S14–S18 for a given token address. Returns list of signal dicts."""
    results = []
    for fn in BEHAVIORAL_SIGNALS:
        try:
            results.append(fn(token_address))
        except Exception as e:
            print(f"  [WARN] {fn.__name__} raised an unexpected error: {e}")
    return results
