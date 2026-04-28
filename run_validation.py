import json
import sys
import time
sys.path.append('.')
from graph_analyzer import calculate_graph_risk

def load_dataset():
    with open("test_dataset.json", "r") as f:
        return json.load(f)

def run_rugshield_on_token(mint_address):
    """
    Simplified scoring - in real implementation this would:
    1. Call P2's full scoring engine
    2. Return the 0-100 risk score
    For testing, we'll just use graph risk
    """
    try:
        # Extract deployer from mint (simplified - real version would query on-chain)
        # For demo, we'll use the mint address as deployer
        graph_risk = calculate_graph_risk(mint_address)
        
        # Simple scoring based on wallet age
        score = 0
        if graph_risk['walletAgeDays'] < 30:
            score += 40
        if graph_risk['deployerFlagged']:
            score += 50
        
        return score
    except Exception as e:
        print(f"Error scoring {mint_address}: {e}")
        return 0

def validate():
    dataset = load_dataset()
    
    results = {
        "true_positives": 0,   # Correctly flagged scam
        "true_negatives": 0,   # Correctly flagged safe
        "false_positives": 0,  # Flagged safe as scam
        "false_negatives": 0,  # Flagged scam as safe
    }
    
    print("Testing on scam tokens...\n")
    for token in dataset["scam_tokens"][:10]:  # Test first 10
        score = run_rugshield_on_token(token)
        print(f"Token: {token[:8]}... Score: {score}")
        
        if score >= 70:
            results["true_positives"] += 1
        else:
            results["false_negatives"] += 1
        
        time.sleep(0.5)
    
    print("\n\nTesting on safe tokens...\n")
    for token in dataset["safe_tokens"][:10]:  # Test first 10
        score = run_rugshield_on_token(token)
        print(f"Token: {token[:8]}... Score: {score}")
        
        if score < 70:
            results["true_negatives"] += 1
        else:
            results["false_positives"] += 1
        
        time.sleep(0.5)
    
    # Calculate metrics
    total = sum(results.values())
    accuracy = (results["true_positives"] + results["true_negatives"]) / total * 100
    
    false_positive_rate = results["false_positives"] / (results["false_positives"] + results["true_negatives"]) * 100
    
    print("\n" + "="*50)
    print("VALIDATION RESULTS")
    print("="*50)
    print(f"True Positives:  {results['true_positives']}")
    print(f"True Negatives:  {results['true_negatives']}")
    print(f"False Positives: {results['false_positives']}")
    print(f"False Negatives: {results['false_negatives']}")
    print(f"\nAccuracy: {accuracy:.1f}%")
    print(f"False Positive Rate: {false_positive_rate:.1f}%")
    
    # Save results
    with open("validation_results.json", "w") as f:
        json.dump({
            "results": results,
            "accuracy": accuracy,
            "false_positive_rate": false_positive_rate
        }, f, indent=2)
    
    print("\n✅ Results saved to validation_results.json")

if __name__ == "__main__":
    validate()
