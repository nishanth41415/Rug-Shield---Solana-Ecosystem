# RugShield P2 — Scoring Output Contract

JSON schema produced by `scorer.py` and `consumer.py`. Saved to `output/<mint_prefix>_score.json`.

## Root object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token_address` | string | yes | Solana mint address (base58, 32 bytes) |
| `deployer_wallet` | string | yes | Deployer wallet resolved on-chain |
| `verified_token` | string \| null | yes | `USDC`, `USDT`, `wSOL`, or `null` |
| `risk_score` | integer | yes | Final score 0–100 |
| `risk_level` | string | yes | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `recommendation` | string | yes | Human-readable verdict |
| `scoring_breakdown` | object | yes | See below |
| `signal_quality` | object | yes | See below |
| `signals` | array | yes | Per-signal results (see below) |
| `signals_run` | integer | yes | Number of signals executed (17) |
| `timestamp` | string | yes | UTC ISO-8601 timestamp |

## `scoring_breakdown`

| Field | Type | Description |
|-------|------|-------------|
| `rule_based_score` | number | Weighted real-signal average (0–100 scale) |
| `ml_model_score` | number | ML scam probability (0–100 scale) |
| `final_score` | integer | Blended final score |
| `blend` | string | Blend formula description |

## `signal_quality`

| Field | Type | Description |
|-------|------|-------------|
| `confidence_level` | string | `low`, `medium`, or `high` |
| `confidence_score` | number | Real-signal ratio 0.0–1.0 |
| `real_signals_count` | integer | Count of `data_source: "real"` signals |
| `fallback_signals_count` | integer | Mock + fallback signals |
| `unavailable_signals_count` | integer | Unavailable signals |
| `signals_real` | string[] | Signal IDs with live data |
| `signals_mock` | string[] | Signal IDs using mock data |
| `signals_unavailable` | string[] | Signal IDs with no data |
| `signals_fallback` | string[] | Signal IDs using fallback heuristics |

## `signals[]` item

| Field | Type | Description |
|-------|------|-------------|
| `signal_id` | string | `S01` … `S18` (S07 not run) |
| `score` | number \| null | 0.0–1.0; `null` when `UNAVAILABLE` / `FALLBACK` |
| `risk_level` | string | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `UNAVAILABLE`, or `FALLBACK` |
| `data_source` | string | `real`, `mock`, `fallback`, or `unavailable` |
| `check` | string | Machine-readable check name |
| `explanation` | string | Human-readable evidence summary |

## Risk level mapping (final score)

| `risk_score` | `risk_level` |
|--------------|--------------|
| 0–29 | LOW |
| 30–59 | MEDIUM |
| 60–79 | HIGH |
| 80–100 | CRITICAL |

## CLI errors

| Condition | Exit code | Message |
|-----------|-----------|---------|
| Missing argument | 1 | Usage help |
| Invalid address | 1 | `[ERROR] Invalid Solana token address` |
| Missing model file | 1 | `[ERROR] ML model not found` |
