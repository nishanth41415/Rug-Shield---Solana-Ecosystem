# RugShield SDK

JavaScript/Node.js SDK for the RugShield risk scoring API.

## Installation

```bash
npm install @rugshield/sdk
```

## Usage

```javascript
const RugShieldSDK = require('@rugshield/sdk');

const sdk = new RugShieldSDK('http://localhost:3000');

// Get risk score for a token
const score = await sdk.score('7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU');
console.log(score);

// Stream real-time alerts for high-risk tokens
sdk.stream((token) => {
  console.log(`High risk token: ${token.mint} - Score: ${token.score}`);
}, 70); // threshold = 70
```

## API

### `score(mintAddress)`
Returns risk score for a token.

**Parameters:**
- `mintAddress` (string) - Solana token mint address

**Returns:** Promise<ScoreResponse>

### `stream(callback, threshold)`
Subscribe to real-time high-risk token alerts.

**Parameters:**
- `callback` (function) - Called when high-risk token detected
- `threshold` (number) - Minimum risk score to trigger alert (default: 70)

**Returns:** WebSocket connection
