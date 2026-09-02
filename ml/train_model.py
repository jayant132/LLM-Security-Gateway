"""Trains an XGBoost classifier to detect prompt-injection/jailbreak attempts.
Saves model + vectorizer artifacts and a metrics.json consumed by the CI
model-quality gate (see redteam/run_redteam.py and .github/workflows).
"""
import json
import sys
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)

sys.path.insert(0, ".")
from ml.features import FeatureBuilder

ARTIFACT_DIR = "ml/artifacts"


def main():
    train_df = pd.read_csv("ml/data/train.csv")
    test_df = pd.read_csv("ml/data/test.csv")

    fb = FeatureBuilder()
    X_train = fb.fit_transform(train_df["text"].tolist())
    y_train = train_df["label"].values
    X_test = fb.transform(test_df["text"].tolist())
    y_test = test_df["label"].values

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "n_train": len(y_train),
        "n_test": len(y_test),
    }

    print(classification_report(y_test, y_pred, target_names=["benign", "malicious"]))
    print("Confusion matrix [[TN,FP],[FN,TP]]:", metrics["confusion_matrix"])
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")

    # Explainability: top features by gain-based importance
    importances = model.feature_importances_
    names = fb.feature_names()
    top_idx = np.argsort(importances)[::-1][:15]
    print("\nTop 15 features by importance:")
    for i in top_idx:
        print(f"  {names[i]:<25} {importances[i]:.4f}")

    model.save_model(f"{ARTIFACT_DIR}/xgb_model.json")
    joblib.dump(fb, f"{ARTIFACT_DIR}/feature_builder.joblib")
    with open(f"{ARTIFACT_DIR}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nArtifacts saved to {ARTIFACT_DIR}/")


if __name__ == "__main__":
    main()
