# RugShield API Documentation

Base URL: `http://localhost:3000`

## Endpoints

### GET /health
Health check endpoint

**Response:**
### GET /score/:mint
Get risk score for a token

**Parameters:**
- `mint` - Solana token mint address

**Example Request:**
```bash
curl http://localhost:3000/score/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
```

**Example Response:**
```json
{
  "mint": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "score": 75,
  "riskLevel": "HIGH",
  "signals": [
    {
      "id": 1,
      "name": "Mint Authority Not Revoked",
      "weight": 20,
      "triggered": true
    }
  ],
  "timestamp": 1714900000
}
```

## Risk Levels

- `LOW` - Score 0-39
- `MEDIUM` - Score 40-69
- `HIGH` - Score 70-100
