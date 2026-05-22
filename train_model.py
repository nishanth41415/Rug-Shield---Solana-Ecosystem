"""
train_model.py — Train a GradientBoostingClassifier on all 18 signal scores.

Reads:  data/labeled_tokens.csv   (produced by scrape_dataset.py)
Saves:  model/scorer.pkl          (the trained model)
        model/feature_importance.json

Usage:
    python train_model.py
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import train_test_split

# ------------------------------------------------------------------ #
#  Paths                                                              #
# ------------------------------------------------------------------ #

BASE        = Path(__file__).parent
DATA_PATH   = BASE / "data" / "labeled_tokens.csv"
MODEL_DIR   = BASE / "model"
MODEL_PATH  = MODEL_DIR / "scorer.pkl"
METRICS_PATH= MODEL_DIR / "metrics.json"
IMPORTANCE_PATH = MODEL_DIR / "feature_importance.json"

MODEL_DIR.mkdir(exist_ok=True)

# 18 feature columns (signal scores)
FEATURES = [
    "s01_mint_authority",
    "s02_freeze_authority",
    "s03_upgradeable",
    "s04_metadata_mutable",
    "s05_lp_lock",
    "s06_deployer_lp",
    "s08_top10_holders",
    "s09_whale_dominance",
    "s10_sybil_clusters",
    "s11_rug_history",
    "s12_wallet_age",
    "s13_suspicious_tx",
    "s14_bot_spike",
    "s15_wash_trading",
    "s16_insider_dump",
    "s17_social_verify",
    "s18_fake_engagement",
]

# Note: s07 is intentionally skipped per the project spec (no Signal 07)
# We have 17 columns above but label them as "18 signals" because
# s08 follows s06 directly (s07 was never built)
# Add a dummy s07 column so downstream code always sees 18 features
FEATURES_WITH_S07 = [
    "s01_mint_authority",
    "s02_freeze_authority",
    "s03_upgradeable",
    "s04_metadata_mutable",
    "s05_lp_lock",
    "s06_deployer_lp",
    "s07_placeholder",      # always 0.0 — signal 07 was not built
    "s08_top10_holders",
    "s09_whale_dominance",
    "s10_sybil_clusters",
    "s11_rug_history",
    "s12_wallet_age",
    "s13_suspicious_tx",
    "s14_bot_spike",
    "s15_wash_trading",
    "s16_insider_dump",
    "s17_social_verify",
    "s18_fake_engagement",
]


# ------------------------------------------------------------------ #
#  Load data                                                          #
# ------------------------------------------------------------------ #

def load_data() -> tuple:
    if not DATA_PATH.exists():
        print(f"[ERROR] Dataset not found at {DATA_PATH}")
        print("Run:  python scrape_dataset.py  first.")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows from {DATA_PATH.name}")
    print(f"  Scam tokens : {(df['label'] == 1).sum()}")
    print(f"  Safe tokens : {(df['label'] == 0).sum()}")

    # Add placeholder s07 column (always 0)
    df["s07_placeholder"] = 0.0

    X = df[FEATURES_WITH_S07].fillna(0.0)
    y = df["label"].astype(int)

    return X, y, df


# ------------------------------------------------------------------ #
#  Train                                                              #
# ------------------------------------------------------------------ #

def train(X_train, y_train) -> GradientBoostingClassifier:
    print("\nTraining GradientBoostingClassifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,       # number of trees
        learning_rate=0.05,     # shrinkage — lower = more robust
        max_depth=4,            # tree depth — controls overfitting
        min_samples_split=10,
        min_samples_leaf=5,
        subsample=0.8,          # stochastic gradient boosting
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("  Training complete.")
    return model


# ------------------------------------------------------------------ #
#  Evaluate                                                           #
# ------------------------------------------------------------------ #

def evaluate(model, X_test, y_test) -> dict:
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy  = round(accuracy_score(y_test, y_pred), 4)
    precision = round(precision_score(y_test, y_pred, zero_division=0), 4)
    recall    = round(recall_score(y_test, y_pred, zero_division=0), 4)
    f1        = round(f1_score(y_test, y_pred, zero_division=0), 4)

    print("\n" + "="*50)
    print("  MODEL EVALUATION")
    print("="*50)
    print(f"  Accuracy  : {accuracy*100:.1f}%")
    print(f"  Precision : {precision*100:.1f}%")
    print(f"  Recall    : {recall*100:.1f}%")
    print(f"  F1 Score  : {f1*100:.1f}%")
    print("="*50)

    cm = confusion_matrix(y_test, y_pred)
    print(f"\n  Confusion Matrix:")
    print(f"    True Negatives  (safe   → safe)  : {cm[0][0]}")
    print(f"    False Positives (safe   → scam)  : {cm[0][1]}")
    print(f"    False Negatives (scam   → safe)  : {cm[1][0]}")
    print(f"    True Positives  (scam   → scam)  : {cm[1][1]}")

    print("\n  Full Classification Report:")
    print(classification_report(y_test, y_pred,
                                 target_names=["safe", "scam"]))

    if accuracy >= 0.80:
        print("  ✅ Accuracy is above 80% — model meets the requirement!")
    else:
        print("  ⚠️  Accuracy is below 80% — consider retraining or collecting more data.")

    return {
        "accuracy":  accuracy,
        "precision": precision,
        "recall":    recall,
        "f1_score":  f1,
        "test_size": len(y_test),
        "confusion_matrix": cm.tolist(),
    }


# ------------------------------------------------------------------ #
#  Feature importance                                                 #
# ------------------------------------------------------------------ #

def save_feature_importance(model) -> None:
    importance = dict(zip(FEATURES_WITH_S07, model.feature_importances_))
    # Sort descending
    importance = dict(sorted(importance.items(),
                              key=lambda x: x[1], reverse=True))

    with open(IMPORTANCE_PATH, "w") as f:
        json.dump({k: round(float(v), 6) for k, v in importance.items()}, f, indent=2)

    print("\n  Top 5 most important signals:")
    for i, (feat, imp) in enumerate(list(importance.items())[:5], 1):
        bar = "█" * int(imp * 100)
        print(f"    {i}. {feat:<25} {imp:.4f}  {bar}")


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #

def main():
    print("\n=== Token Risk ML Model Training ===\n")

    # Load
    X, y, df = load_data()

    # Split — 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train size : {len(X_train)}")
    print(f"  Test size  : {len(X_test)}")

    # Train
    model = train(X_train, y_train)

    # Evaluate
    metrics = evaluate(model, X_test, y_test)

    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"\n  Model saved → {MODEL_PATH}")

    # Save metrics
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved → {METRICS_PATH}")

    # Save feature importance
    save_feature_importance(model)
    print(f"  Feature importance saved → {IMPORTANCE_PATH}")

    print(f"\nNext step: python scorer.py <any_token_address>")


if __name__ == "__main__":
    main()
