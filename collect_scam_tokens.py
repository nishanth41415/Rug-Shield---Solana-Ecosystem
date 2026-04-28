import requests
import json

# Scrape known rug pulls from public sources
# This is a simplified version - you'd scrape from RugCheck, Solsniffer, etc.

KNOWN_SCAM_TOKENS = [
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "9yKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgBsV",
    # Add 98 more from RugCheck history...
]

KNOWN_SAFE_TOKENS = [
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    # Add 98 more verified safe tokens...
]

def save_dataset():
    dataset = {
        "scam_tokens": KNOWN_SCAM_TOKENS,
        "safe_tokens": KNOWN_SAFE_TOKENS
    }
    with open("test_dataset.json", "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"✅ Dataset saved: {len(KNOWN_SCAM_TOKENS)} scam, {len(KNOWN_SAFE_TOKENS)} safe")

if __name__ == "__main__":
    save_dataset()
