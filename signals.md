# Signals Documentation

All 18 signals used by the RugShield scoring engine.
Each signal outputs a score from **0.0 (safe) to 1.0 (critical risk)**.

---

## On-Chain Authority Signals (S01–S04)

### S01 — Mint Authority Check
| Field | Value |
|---|---|
| Weight | 0.90 (Critical) |
| What it detects | Whether the token creator can still print new tokens |
| Why it matters | An active mint authority means the deployer can inflate supply at any time, dumping on holders |
| Score logic | 0.9 if mint authority is active, 0.0 if revoked |
| Example trigger | New memecoin launched with mint authority never revoked |

---

### S02 — Freeze Authority Check
| Field | Value |
|---|---|
| Weight | 0.70 (High) |
| What it detects | Whether the creator can freeze token accounts and prevent holders from selling |
| Why it matters | A freeze authority allows the deployer to trap holders by blocking all transfers |
| Score logic | 0.7 if freeze authority is active, 0.0 if revoked |
| Example trigger | Token where deployer freezes wallets after price pump to prevent sells |

---

### S03 — Upgradeable Contract Check
| Field | Value |
|---|---|
| Weight | 0.60 (High) |
| What it detects | Whether the program logic can be swapped out after deployment |
| Why it matters | An upgradeable program means the rules of the token can be changed silently after launch |
| Score logic | 0.75 if upgradeable, 0.05 if immutable |
| Example trigger | Project upgrades contract to add hidden fee after gaining trust |

---

### S04 — Metadata Mutability Check
| Field | Value |
|---|---|
| Weight | 0.50 (Medium) |
| What it detects | Whether the token name, symbol, or image URI can be changed |
| Why it matters | Mutable metadata allows identity switching — a scam token can impersonate a legitimate one |
| Score logic | 0.55 if mutable, 0.0 if immutable |
| Example trigger | Token changes its name and logo to mimic a trending project |

---

## Liquidity Signals (S05–S06)

### S05 — LP Lock Status Check
| Field | Value |
|---|---|
| Weight | 0.80 (Critical) |
| What it detects | What percentage of liquidity pool tokens are locked |
| Why it matters | Unlocked LP means the deployer can drain all liquidity instantly (classic rug pull) |
| Score logic | 1.0 − locked_percent (fully locked = 0.0, fully unlocked = 1.0) |
| Example trigger | Deployer removes all liquidity within minutes of launch |

---

### S06 — Deployer LP Concentration Check
| Field | Value |
|---|---|
| Weight | 0.75 (Critical) |
| What it detects | What fraction of LP tokens the deployer wallet holds |
| Why it matters | If the deployer controls most of the LP, they can rug at any moment |
| Score logic | Directly equals deployer_lp_percent (0 → safe, 1 → critical) |
| Example trigger | Deployer holds 80% of LP tokens and removes them after launch pump |

---

## Holder Distribution Signals (S08–S09)

### S08 — Top 10 Holder Concentration
| Field | Value |
|---|---|
| Weight | 0.65 (High) |
| What it detects | Combined supply percentage held by the top 10 wallets |
| Why it matters | High concentration means a coordinated sell-off can collapse the token price |
| Score logic | Directly equals top_10_concentration (capped at 1.0) |
| Example trigger | Top 10 wallets hold 90% of supply and dump simultaneously |

---

### S09 — Whale Dominance Check
| Field | Value |
|---|---|
| Weight | 0.70 (High) |
| What it detects | Supply percentage held by the single largest wallet |
| Why it matters | One whale can single-handedly crash the price with a single transaction |
| Score logic | Tiered: ≥50% → 0.95, ≥30% → 0.85, ≥10% → 0.65, ≥5% → 0.4, else 0.1 |
| Example trigger | Single wallet holds 60% of supply and sells everything at peak |

---

## Graph-Based Signals — from P1 (S10–S13)

### S10 — Sybil Wallet Clustering
| Field | Value |
|---|---|
| Weight | 0.75 (High) |
| What it detects | Number of fake wallet clusters around the deployer (wallets funded from the same source) |
| Why it matters | Sybil wallets are used to fake organic trading activity and hide insider concentration |
| Score logic | 0 clusters → 0.0, 1 → 0.4, 2 → 0.65, 3 → 0.8, 4+ → 0.95 |
| Data source | P1 graph analyzer (calculate_graph_risk → sybilClusters) |
| Example trigger | Deployer controls 20 wallets that all buy at launch to fake volume |

---

### S11 — Previous Rug Pull History
| Field | Value |
|---|---|
| Weight | 0.90 (Critical) |
| What it detects | Whether the deployer or connected wallets have rugged before |
| Why it matters | Serial ruggers reuse wallets or fund new ones from the same source |
| Score logic | Flagged deployer → 0.95, hop 1 → 0.75, hop 2 → 0.55, hop 3 → 0.35, clean → 0.05 |
| Data source | P1 graph analyzer (deployerFlagged + hopDistance) |
| Example trigger | Same deployer wallet launched 3 rugged tokens in the past 6 months |

---

### S12 — Wallet Age Under 30 Days
| Field | Value |
|---|---|
| Weight | 0.80 (Critical) |
| What it detects | How old the deployer wallet is in days |
| Why it matters | Rug pullers create fresh wallets to avoid history checks |
| Score logic | <7 days → 0.95, <30 days → 0.75, <90 days → 0.4, 90+ days → 0.05 |
| Data source | P1 graph analyzer (walletAgeDays) |
| Example trigger | Token deployed from a wallet created 3 days ago with no prior activity |

---

### S13 — Suspicious Transaction Patterns
| Field | Value |
|---|---|
| Weight | 0.65 (High) |
| What it detects | Circular fund flows and layering in the wallet graph |
| Why it matters | Layered transactions are used to obscure the origin of funds and fake trading activity |
| Score logic | Weighted combo: 0.5 × sybil_score + 0.5 × proximity_score |
| Data source | P1 graph analyzer (sybilClusters + hopDistance) |
| Example trigger | Funds routed through 5 intermediate wallets before reaching the deployer |

---

## Behavioral Signals (S14–S16)

### S14 — Bot Activity Spike Detection
| Field | Value |
|---|---|
| Weight | 0.60 (High) |
| What it detects | Unnatural transaction volume spikes at launch (many txns per second) |
| Why it matters | Bots are used to simulate organic demand and manipulate price at launch |
| Score logic | spike_ratio = peak_volume / median_volume: <3x → 0.1, <6x → 0.45, <10x → 0.7, 10x+ → 0.9 |
| Example trigger | 500 transactions in first 10 seconds of launch, all from bot wallets |

---

### S15 — Wash Trading Detection via Z-score
| Field | Value |
|---|---|
| Weight | 0.65 (High) |
| What it detects | Wallets that repeatedly buy and sell equal amounts to fake volume |
| Why it matters | Wash trading inflates volume metrics, making a low-interest token look active |
| Score logic | Proportion of wallets with buy/sell ratio > 0.8, scaled up by 1.5x |
| Example trigger | Same 10 wallets cycling tokens back and forth 50 times to show fake volume |

---

### S16 — Sudden Dump Pattern from Insider Wallets
| Field | Value |
|---|---|
| Weight | 0.85 (Critical) |
| What it detects | Pre-launch wallets that received tokens and sold quickly after launch |
| Why it matters | Insiders who dump immediately after launch is the most direct indicator of a coordinated rug |
| Score logic | 0.6 × worst_insider_score + 0.4 × avg_insider_score |
| Example trigger | 5 wallets received tokens pre-launch and sold 90% within the first 2 hours |

---

## Social Signals (S17–S18)

### S17 — Twitter/Telegram Account Verification
| Field | Value |
|---|---|
| Weight | 0.55 (Medium) |
| What it detects | Existence and age of the project's social media accounts |
| Why it matters | Anonymous projects with no social presence or brand-new accounts are high risk |
| Score logic | No accounts → 0.85, <7 days old → 0.8, <30 days → 0.55, <180 days → 0.3, 180+ → 0.1 |
| Status | Currently mocked — swap in Twitter API v2 / Telegram Bot API when keys available |
| Example trigger | Project has Twitter account created 1 day before token launch |

---

### S18 — Fake Engagement Detection via NLP
| Field | Value |
|---|---|
| Weight | 0.50 (Medium) |
| What it detects | Bot-like patterns in social posts: repetition, hype keywords, very short messages |
| Why it matters | Fake engagement makes scam projects appear to have a real community |
| Score logic | 0.4 × repetition_score + 0.4 × hype_score + 0.2 × short_post_score |
| Status | Currently mocked — swap in real Telegram/Twitter scraper when available |
| Example trigger | Telegram channel where 80% of messages are identical "100x GUARANTEED buy now" posts |

---

## Score to Risk Level Mapping

| Score Range | Risk Level | Meaning |
|---|---|---|
| 0.0 – 0.29 | LOW | Token appears safe |
| 0.3 – 0.59 | MEDIUM | Proceed with caution |
| 0.6 – 0.79 | HIGH | Strong red flags present |
| 0.8 – 1.0 | CRITICAL | Very likely a scam |

## Final Risk Score (0–100)

The final score combines:
- **60%** weighted average of all 18 rule-based signal scores
- **40%** ML model probability (GradientBoostingClassifier)

| Final Score | Risk Level | Recommendation |
|---|---|---|
| 0–29 | LOW | Safe to consider |
| 30–59 | MEDIUM | Proceed with caution |
| 60–79 | HIGH | Avoid unless verified |
| 80–100 | CRITICAL | Do not buy |
