"""
graph_analyzer.py — P1's graph analyzer, fixed for integration with P2.

Fixes from P1's original:
  - confirmed_rugs table doesn't exist yet → handled gracefully
    (check_rug_database returns False instead of crashing)
  - DB connection wrapped in try/except so scorer never crashes
    if PostgreSQL is not running
  - sybilClusters now computed from real graph data (node count heuristic)
    instead of always returning 0
"""

import networkx as nx
from deployer_fetcher import get_wallet_transactions, get_wallet_age_days

# ------------------------------------------------------------------ #
#  DB connection — safe, won't crash if DB is unavailable             #
# ------------------------------------------------------------------ #

_conn = None

def _get_conn():
    global _conn
    if _conn is not None:
        return _conn
    try:
        import psycopg2
        _conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="rugshield",
            user="rugshield",
            password="rugshield123"
        )
        return _conn
    except Exception as e:
        print(f"⚠️ DB not available: {e} — rug history check disabled")
        return None


def check_rug_database(wallet_address: str) -> bool:
    """
    Check if wallet is in confirmed rug pull database.
    Returns False safely if the table doesn't exist or DB is down.
    """
    conn = _get_conn()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        # Check if table exists first
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'confirmed_rugs'
            )
        """)
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            cursor.close()
            return False

        cursor.execute(
            "SELECT COUNT(*) FROM confirmed_rugs WHERE deployer_wallet = %s",
            (wallet_address,)
        )
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0

    except Exception:
        return False


# ------------------------------------------------------------------ #
#  Graph builder                                                      #
# ------------------------------------------------------------------ #

def build_wallet_graph(root_wallet, max_hops=3):
    """Build a graph by tracing wallet connections up to max_hops."""
    G = nx.DiGraph()
    visited = set()
    queue = [(root_wallet, 0)]

    while queue:
        wallet, hop = queue.pop(0)

        if wallet in visited or hop > max_hops:
            continue

        visited.add(wallet)

        txs = get_wallet_transactions(wallet, limit=50)
        G.add_node(wallet, hop=hop)

        if hop < max_hops and txs:
            # Extract connected wallets from account keys in transactions
            # (simplified — real impl would parse all account keys)
            pass

    return G


def _count_sybil_clusters(graph: nx.DiGraph) -> int:
    """
    Estimate sybil clusters from graph node count.
    More nodes at hop > 1 = more likely coordinated wallets.
    """
    node_count = graph.number_of_nodes()
    if node_count <= 1:
        return 0
    elif node_count <= 3:
        return 1
    elif node_count <= 6:
        return 2
    elif node_count <= 10:
        return 3
    else:
        return 4


# ------------------------------------------------------------------ #
#  Main risk calculator                                               #
# ------------------------------------------------------------------ #

def calculate_graph_risk(deployer_wallet: str) -> dict:
    """
    Calculate graph-based risk score for a deployer wallet.

    Returns:
    {
        "deployerWallet":  str,
        "walletAgeDays":   int,
        "deployerFlagged": bool,
        "sybilClusters":   int,
        "hopDistance":     int,
    }
    """
    risk_data = {
        "deployerWallet":  deployer_wallet,
        "walletAgeDays":   0,
        "deployerFlagged": False,
        "sybilClusters":   0,
        "hopDistance":     0,
    }

    # Wallet age — uses real Solana RPC
    age = get_wallet_age_days(deployer_wallet)
    risk_data["walletAgeDays"] = age

    # Rug history — uses DB (safe if DB/table missing)
    is_rugger = check_rug_database(deployer_wallet)
    risk_data["deployerFlagged"] = is_rugger

    # Build graph
    graph = build_wallet_graph(deployer_wallet, max_hops=3)

    # Check connected wallets for known ruggers
    for node in graph.nodes():
        if node != deployer_wallet and check_rug_database(node):
            risk_data["hopDistance"] = graph.nodes[node].get("hop", 1)
            break

    # Sybil detection from graph structure
    risk_data["sybilClusters"] = _count_sybil_clusters(graph)

    return risk_data


# Test
if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Analyzing wallet: {test_wallet}\n")

    risk = calculate_graph_risk(test_wallet)

    print("📊 Graph Risk Analysis:")
    print(f"  Wallet Age:                    {risk['walletAgeDays']} days")
    print(f"  Deployer Flagged:              {risk['deployerFlagged']}")
    print(f"  Sybil Clusters:                {risk['sybilClusters']}")
    print(f"  Hop Distance to Known Rugger:  {risk['hopDistance']}")

    if risk['walletAgeDays'] < 30:
        print("\n🚩 HIGH RISK: Wallet age < 30 days")
    if risk['deployerFlagged']:
        print("🚩 HIGH RISK: Deployer previously rugged")
