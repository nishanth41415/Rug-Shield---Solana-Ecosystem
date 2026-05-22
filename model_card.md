# Model Card — RugShield Token Risk Classifier

## Overview

| Field | Value |
|---|---|
| Model name | RugShield Token Risk Classifier |
| Model type | GradientBoostingClassifier (scikit-learn) |
| Task | Binary classification — scam (1) vs safe (0) |
| Output | Probability of scam (0.0–1.0), combined with rule-based signals into a 0–100 risk score |
| Version | 1.0 |
| Built by | P2 — Scoring Engine Team |

---

## Training Data

| Field | Value |
|---|---|
| Total tokens | 500 |
| Scam tokens | 250 (50%) |
| Safe tokens | 250 (50%) |
| Sources | RugCheck API, Solsniffer API, deterministic mock data |
| Label definition | Scam = confirmed rug pull or score < 30 on RugCheck/Solsniffer. Safe = score > 80 |
| Train / test split | 80% train (400 tokens), 20% test (100 tokens) |

---

## Features (18 Signals)

All features are normalized signal scores in the range **0.0 – 1.0**.

| Rank | Feature | Importance | Signal |
|---|---|---|---|
| 1 | s10_sybil_clusters | 25.2% | Sybil wallet clustering |
| 2 | s18_fake_engagement | 16.9% | Fake NLP engagement |
| 3 | s14_bot_spike | 12.5% | Bot activity spike |
| 4 | s01_mint_authority | 10.1% | Mint authority active |
| 5 | s03_upgradeable | 9.5% | Upgradeable contract |
| 6 | s16_insider_dump | 8.0% | Insider dump pattern |
| 7 | s02_freeze_authority | 6.0% | Freeze authority active |
| 8 | s04_metadata_mutable | 3.6% | Mutable metadata |
| 9 | s12_wallet_age | 3.2% | Wallet age under 30 days |
| 10 | s13_suspicious_tx | 1.7% | Suspicious transaction patterns |
| 11 | s09_whale_dominance | 1.2% | Whale dominance |
| 12 | s06_deployer_lp | 0.7% | Deployer LP concentration |
| 13 | s05_lp_lock | 0.6% | LP lock status |
| 14 | s17_social_verify | 0.3% | Social account verification |
| 15 | s08_top10_holders | 0.3% | Top 10 holder concentration |
| 16 | s15_wash_trading | 0.2% | Wash trading Z-score |
| 17 | s11_rug_history | 0.1% | Previous rug pull history |
| 18 | s07_placeholder | 0.0% | Not used (Signal 07 not built) |

---

## Model Hyperparameters

| Parameter | Value | Reason |
|---|---|---|
| n_estimators | 200 | Enough trees for stable predictions |
| learning_rate | 0.05 | Low rate prevents overfitting |
| max_depth | 4 | Controls tree complexity |
| min_samples_split | 10 | Avoids splits on tiny groups |
| min_samples_leaf | 5 | Ensures each leaf has meaningful data |
| subsample | 0.8 | Stochastic boosting for robustness |
| random_state | 42 | Reproducible results |

---

## Accuracy Metrics (Test Set — 100 tokens)

| Metric | Score |
|---|---|
| Accuracy | 100% |
| Precision | 100% |
| Recall | 100% |
| F1 Score | 100% |

### Confusion Matrix

| | Predicted Safe | Predicted Scam |
|---|---|---|
| **Actual Safe** | 50 (True Negative) | 0 (False Positive) |
| **Actual Scam** | 0 (False Negative) | 50 (True Positive) |

---

## Final Score Formula

The final 0–100 risk score combines rule-based and ML signals:

```
final_score = (0.60 × weighted_signal_average + 0.40 × ml_probability) × 100
```

| Component | Weight | Description |
|---|---|---|
| Rule-based signals | 60% | Weighted average of all 18 signal scores |
| ML model probability | 40% | GradientBoosting scam probability |

---

## Known Limitations

**Mock data dependency**
The model was trained on mock/synthetic data for the hackathon. Signal scores for S05–S18 are generated from deterministic hash functions rather than real blockchain data. Accuracy will vary on real-world tokens until live data sources are connected.

**S17 and S18 are mocked**
Twitter and Telegram signals require API keys not available at time of training. These signals return mock data until real API credentials are provided.

**S10–S13 require P1's database**
Graph-based signals depend on P1's PostgreSQL database of confirmed rug wallets. Without the live DB connection, these signals fall back to hash-based mocks.

**No Signal 07**
Signal 07 was not built per the project specification. A zero-value placeholder is used so the feature vector stays consistent.

**Class balance**
Training data is perfectly balanced (50/50 scam/safe). Real-world token distribution may skew toward more safe tokens, which could affect precision on the scam class.

---

## How to Retrain

```bash
# Step 1 — collect fresh data
python3 scrape_dataset.py --count 1000

# Step 2 — retrain the model
python3 train_model.py

# Step 3 — test on a token
python3 scorer.py <token_address>
```

---

## How to Improve Accuracy (Day 3 Tuning)

If accuracy drops below 80% after connecting real data, try these:

```python
# In train_model.py, adjust these parameters:
GradientBoostingClassifier(
    n_estimators=300,      # increase from 200
    learning_rate=0.03,    # lower from 0.05
    max_depth=5,           # increase from 4
    subsample=0.7,         # lower from 0.8
)
```

---

## Files

| File | Description |
|---|---|
| `model/scorer.pkl` | Trained model binary |
| `model/metrics.json` | Accuracy, precision, recall, F1 |
| `model/feature_importance.json` | Per-signal importance ranking |
| `data/labeled_tokens.csv` | Training dataset |
| `signals/signals.py` | Signals S01–S09 |
| `signals/graph_signals.py` | Signals S10–S13 (P1 integration) |
| `signals/behavioral_signals.py` | Signals S14–S18 |
| `train_model.py` | Model training script |
| `scorer.py` | Final scoring pipeline |
| `signals.md` | Signal documentation |
