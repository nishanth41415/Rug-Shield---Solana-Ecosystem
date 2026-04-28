import networkx as nx
import psycopg2
from deployer_fetcher import get_wallet_transactions, get_wallet_age_days

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="rugshield",
    user="rugshield",
    password="rugshield123"
)

def build_wallet_graph(root_wallet, max_hops=3):
    """Build a graph by tracing wallet connections up to max_hops"""
    G = nx.DiGraph()
    visited = set()
    queue = [(root_wallet, 0)]
    
    while queue:
        wallet, hop = queue.pop(0)
        
        if wallet in visited or hop > max_hops:
            continue
        
        visited.add(wallet)
        print(f"🔍 Scanning wallet: {wallet} (hop {hop})")
        
        # Get transactions for this wallet
        txs = get_wallet_transactions(wallet, limit=50)
        
        for tx in txs:
            # Extract connected wallets from transaction
            # (Simplified - real implementation would parse account keys)
            # For demo, we'll just add the wallet to the graph
            G.add_node(wallet, hop=hop)
        
        if hop < max_hops:
            # In real implementation, extract connected wallets and add to queue
            pass
    
    return G

def check_rug_database(wallet_address):
    """Check if wallet is in confirmed rug pull database"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM confirmed_rugs WHERE deployer_wallet = %s",
        (wallet_address,)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0

def calculate_graph_risk(deployer_wallet):
    """Calculate graph-based risk score for a deployer wallet"""
    risk_data = {
        "deployerWallet": deployer_wallet,
        "walletAgeDays": 0,
        "deployerFlagged": False,
        "sybilClusters": 0,
        "hopDistance": 0
    }
    
    # Check wallet age
    age = get_wallet_age_days(deployer_wallet)
    risk_data["walletAgeDays"] = age
    
    # Check if deployer is in rug database
    is_rugger = check_rug_database(deployer_wallet)
    risk_data["deployerFlagged"] = is_rugger
    
    # Build graph (3 hops)
    graph = build_wallet_graph(deployer_wallet, max_hops=3)
    
    # Check if any connected wallet is a known rugger
    for node in graph.nodes():
        if check_rug_database(node):
            risk_data["hopDistance"] = graph.nodes[node].get("hop", 0)
            break
    
    # Sybil detection (placeholder - real implementation would check funding patterns)
    risk_data["sybilClusters"] = 0
    
    return risk_data

# Test it
if __name__ == "__main__":
    test_wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    print(f"Analyzing wallet: {test_wallet}\n")
    
    risk = calculate_graph_risk(test_wallet)
    
    print("\n📊 Graph Risk Analysis:")
    print(f"  Wallet Age: {risk['walletAgeDays']} days")
    print(f"  Deployer Flagged: {risk['deployerFlagged']}")
    print(f"  Sybil Clusters: {risk['sybilClusters']}")
    print(f"  Hop Distance to Known Rugger: {risk['hopDistance']}")
    
    if risk['walletAgeDays'] < 30:
        print("\n🚩 HIGH RISK: Wallet age < 30 days")
    if risk['deployerFlagged']:
        print("🚩 HIGH RISK: Deployer previously rugged")
