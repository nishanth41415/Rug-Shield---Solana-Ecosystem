# RugShield

Real-time, event-driven risk intelligence pipeline for the Solana ecosystem.
It listens for token mint activity, queues events in Redis, and evaluates
on-chain and deployer signals for potential rug-pull risk.

## Highlights

- Event-driven Solana mint monitoring
- Redis Streams for decoupled processing
- PostgreSQL-backed known-rug checks
- NetworkX graph analysis for deployer relationships
- Configurable infrastructure through environment variables
- Offline validation workflow with a bundled sample dataset

## Architecture

```text
Solana RPC -> Mint listener -> Redis Stream -> Risk analysis
                                               |-> Wallet activity
                                               |-> Graph signals
                                               +-> Known-rug database
```

## Components

- `solana_listener.py` - observes Solana mint events
- `redis_queue.py` - reads and writes queued events
- `deployer_fetcher.py` - retrieves deployer activity
- `graph_analyzer.py` - calculates graph-based risk signals
- `run_validation.py` - validates the scoring approach against sample data
- `collect_scam_tokens.py` - dataset collection utility

## Local setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate it on Windows: `.venv\Scripts\activate`
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Configure the variables shown in `.env.example`.
5. Start infrastructure: `docker compose up -d`
6. Run the listener: `python solana_listener.py`

Inspect captured events with:

```text
redis-cli XRANGE solana:mint:events - + COUNT 5
```

## Offline validation

Run `python run_validation.py` to evaluate the included test dataset without
starting the live listener.

The bundled dataset is deliberately small and currently produces 50% accuracy.
That result is documented rather than presented as production performance; the
next engineering step is expanding labeled data and replacing placeholder
signals with fully parsed on-chain relationships.

## Configuration and safety

Keep RPC credentials, database URLs, and API keys in local environment
variables. Do not commit wallet secrets or production credentials. RugShield is
a research prototype; its scores are signals, not financial advice.
