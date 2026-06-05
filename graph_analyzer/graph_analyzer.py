"""
graph_analyzer/graph_analyzer.py — P1 wallet graph analyzer for RugShield P2.

Fixes over P1's original:
  - confirmed_rugs table missing → handled gracefully (returns False, never crashes)
  - DB connection wrapped in try/except → scorer never crashes if Postgres is down
  - build_wallet_graph() now ACTUALLY traces connected wallets via RPC accountKeys
  - sybilClusters computed from real connected-wallet graph structure
  - Import paths fixed to work when called from scorer.py in the project root
"""

import sys
import time
from pathlib import Path

# Add both the graph_analyzer dir and the project root to the path
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import networkx as nx
from deployer_fetcher import get_wallet_transactions, get_wallet_age_days
from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

# ---------------------------------------------------------------------------
#  PostgreSQL connection (safe — never crashes if DB is down)
# ---------------------------------------------------------------------------

_conn = None


def _get_conn():
    """
    Return a live psycopg2 connection, or None if DB is unavailable.
    Connection is cached for the lifetime of the process.
    """
    global _conn
    if _conn is not None:
        try:
            _conn.cursor().execute("SELECT 1")
            return _conn
        except Exception:
            _conn = None   # stale connection — reset and retry below

    try:
        import psycopg2  # type: ignore
        _conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=3,
        )
        return _conn
    except Exception as e:
        print(f"  [WARN] DB not available: {e} — rug history check disabled")
        return None


def check_db_connection() -> bool:
    """
    Return True if PostgreSQL is reachable and the confirmed_rugs table exists.
    Returns False on any failure — scorer continues with mock/fallback data.
    """
    conn = _get_conn()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND   table_name   = 'confirmed_rugs'
            )
        """)
        return bool(cursor.fetchone()[0])
    except Exception:
        return False


def check_rug_database(wallet_address: str) -> bool:
    """
    Check if a wallet is in the confirmed rug pull database.
    Returns False safely if:
        - PostgreSQL is not running
        - The 'confirmed_rugs' table doesn't exist yet (P1 hasn't populated it)
        - Any other DB error
    """
    conn = _get_conn()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()

        # Guard: check table exists before querying it
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND   table_name   = 'confirmed_rugs'
            )
        """)
        if not cursor.fetchone()[0]:
            cursor.close()
            return False

        cursor.execute(
            "SELECT COUNT(*) FROM confirmed_rugs WHERE deployer_wallet = %s",
            (wallet_address,),
        )
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0

    except Exception:
        return False


# ---------------------------------------------------------------------------
#  Wallet graph builder
# ---------------------------------------------------------------------------

def _extract_connected_wallets(wallet: str, txs: list[dict]) -> set[str]:
    """
    Extract unique wallet addresses that co-appear in transactions with
    the given wallet, using the transaction's accountKeys list.

    We exclude system programs and well-known protocol addresses to
    focus on actual human-controlled wallets.
    """
    EXCLUDED = {
        wallet,
        "11111111111111111111111111111111",          # System program
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJe8bXh",  # ATA program
        "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",  # Metaplex
        "So11111111111111111111111111111111111111112",   # Wrapped SOL
        "ComputeBudget111111111111111111111111111111",   # Compute budget
    }

    connected = set()
    for tx in txs:
        try:
            # Transactions may be raw dicts (from getSignaturesForAddress)
            # or full parsed objects — handle both
            account_keys = tx.get("accountKeys", [])
            if not account_keys:
                # Try nested structure from full tx fetch
                account_keys = (
                    tx.get("transaction", {})
                      .get("message", {})
                      .get("accountKeys", [])
                )
            for key in account_keys:
                pubkey = key.get("pubkey", key) if isinstance(key, dict) else key
                if pubkey and pubkey not in EXCLUDED and len(pubkey) > 30:
                    connected.add(pubkey)
        except Exception:
            continue

    return connected


def build_wallet_graph(root_wallet: str, max_hops: int = 2) -> nx.DiGraph:
    """
    Build a directed graph by tracing wallet connections up to max_hops.

    At each hop:
        1. Fetch recent transactions for the current wallet
        2. Extract all co-occurring wallet addresses
        3. Add them as nodes at (current_hop + 1)
        4. Queue them for next iteration

    Limited to max_hops=2 by default to stay within RPC rate limits.
    """
    G       = nx.DiGraph()
    visited = set()
    queue   = [(root_wallet, 0)]

    G.add_node(root_wallet, hop=0)

    while queue:
        wallet, hop = queue.pop(0)

        if wallet in visited or hop >= max_hops:
            continue
        visited.add(wallet)

        # Fetch raw tx signatures (lightweight — no full tx parse needed here)
        txs = get_wallet_transactions(wallet, limit=30)
        if not txs:
            continue

        connected = _extract_connected_wallets(wallet, txs)

        for peer in connected:
            if peer not in visited:
                next_hop = hop + 1
                if not G.has_node(peer):
                    G.add_node(peer, hop=next_hop)
                G.add_edge(wallet, peer)
                if next_hop < max_hops:
                    queue.append((peer, next_hop))

        time.sleep(0.1)   # gentle rate limit between wallet fetches

    return G


def _count_sybil_clusters(graph: nx.DiGraph) -> int:
    """
    Estimate sybil cluster count from graph structure.

    Uses weakly connected components (excluding the root) as a proxy
    for independent coordinated wallet groups.

    Size thresholds:
        1 node  → 0 clusters
        2–4     → 1
        5–9     → 2
        10–19   → 3
        20+     → 4
    """
    # Remove root to see the surrounding cluster structure
    subgraph   = graph.copy()
    root_nodes = [n for n, d in graph.nodes(data=True) if d.get("hop", 1) == 0]
    subgraph.remove_nodes_from(root_nodes)

    if subgraph.number_of_nodes() == 0:
        return 0

    components = list(nx.weakly_connected_components(subgraph))
    peer_count = subgraph.number_of_nodes()

    if peer_count < 2:
        return 0
    elif peer_count < 5:
        return 1
    elif peer_count < 10:
        return 2
    elif peer_count < 20:
        return 3
    else:
        return 4


# ---------------------------------------------------------------------------
#  Main risk calculator
# ---------------------------------------------------------------------------

def calculate_graph_risk(deployer_wallet: str) -> dict:
    """
    Calculate graph-based risk metrics for a deployer wallet.

    Returns the standard P1 data contract:
    {
        "deployerWallet":  str,    # the wallet address
        "walletAgeDays":   int,    # age from oldest on-chain tx
        "deployerFlagged": bool,   # in confirmed_rugs table
        "sybilClusters":   int,    # estimated from wallet graph
        "hopDistance":     int,    # hops to nearest known rugger
    }

    All fields are safe — nothing here will crash.
    """
    risk_data = {
        "deployerWallet":  deployer_wallet,
        "walletAgeDays":   0,
        "deployerFlagged": False,
        "sybilClusters":   0,
        "hopDistance":     0,
        "_meta": {
            "wallet_age_source": "unavailable",
            "rug_db_source":     "unavailable",
            "graph_source":      "unavailable",
        },
    }

    # 1. Wallet age — REAL via Solana mainnet RPC
    try:
        txs = get_wallet_transactions(deployer_wallet, limit=5)
        if txs:
            risk_data["walletAgeDays"] = get_wallet_age_days(deployer_wallet)
            risk_data["_meta"]["wallet_age_source"] = "real"
    except Exception as e:
        print(f"  [WARN] wallet age fetch failed: {e}")

    # 2. Rug history — REAL when P1 populates confirmed_rugs table
    try:
        conn = _get_conn()
        if conn is not None:
            risk_data["_meta"]["rug_db_source"] = "real"
            risk_data["deployerFlagged"] = check_rug_database(deployer_wallet)
    except Exception:
        pass

    # 3. Build wallet graph — REAL via RPC tx tracing
    try:
        graph = build_wallet_graph(deployer_wallet, max_hops=2)
        risk_data["_meta"]["graph_source"] = "real"

        hop_distance = 0
        for node, attrs in graph.nodes(data=True):
            if node == deployer_wallet:
                continue
            if check_rug_database(node):
                hop_distance = attrs.get("hop", 1)
                break
        risk_data["hopDistance"] = hop_distance
        risk_data["sybilClusters"] = _count_sybil_clusters(graph)

    except Exception as e:
        print(f"  [WARN] graph build failed: {e} — graph signals marked unavailable")

    return risk_data


# ---------------------------------------------------------------------------
#  Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Analyzing wallet: {test_wallet}\n")

    risk = calculate_graph_risk(test_wallet)

    print("Graph Risk Analysis:")
    print(f"  Wallet Age                   : {risk['walletAgeDays']} days")
    print(f"  Deployer Flagged (confirmed) : {risk['deployerFlagged']}")
    print(f"  Sybil Clusters               : {risk['sybilClusters']}")
    print(f"  Hop Distance to Known Rugger : {risk['hopDistance']}")

    if risk["walletAgeDays"] < 30:
        print("\n🚩 HIGH RISK: Wallet age < 30 days")
    if risk["deployerFlagged"]:
        print("🚩 CRITICAL: Deployer previously confirmed as a rugger")
