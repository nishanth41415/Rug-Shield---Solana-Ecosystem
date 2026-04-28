# RugShield - P1 Pipeline

## Overview
This service listens to the Solana blockchain and captures real-time token mint events.  
Each event is pushed into a Redis stream for further processing by the scoring engine.

---


## Tech Stack
- Solana RPC
- Redis (Streams)
- PostgreSQL
- Docker

---

## How to Run

### 1. Start services
docker-compose up

### 2. Run the listener
python solana_listener.py

### 3. Verify events
redis-cli
XRANGE solana:mint:events - + COUNT 5

---

## Output
Real-time Solana token mint events are pushed into:
Stream: solana:mint:events

Event format:
{
  "mintAddress": "string",
  "timestamp": "number",
  "programId": "string"
}# Rug-Shield---Solana-Ecosystem

# RugShield — Real-Time Risk Intelligence Engine for Solana

Real-time, event-driven risk intelligence engine that evaluates every newly deployed Solana token across 18 on-chain and behavioral signals.

## Architecture
