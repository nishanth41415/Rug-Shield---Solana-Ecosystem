# RugShield Data Contracts

## 1. Redis Event Schema (P1 → P2)

Stream: solana:mint:events

```json
{
  "mintAddress": "string",
  "timestamp": "number",
  "programId": "string"
}
{
  "mint": "string",
  "score": "number",
  "riskLevel": "LOW | MEDIUM | HIGH",
  "signals": [
    {
      "id": "string",
      "weight": "number",
      "triggered": "boolean"
    }
  ]
}
{
  "event": "new_token",
  "data": { }
}

---


