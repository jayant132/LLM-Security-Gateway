"""Model quality gate: fails the build if the trained classifier's metrics
regress below acceptable thresholds. Run after ml/train_model.py in CI.
This is the ML equivalent of the red-team security gate - the same
"don't ship a regression" discipline applied to a model artifact instead
of a rules engine.
"""
import json
import sys

THRESHOLDS = {"f1": 0.80, "recall": 0.80, "roc_auc": 0.85}


def main():
    with open("ml/artifacts/metrics.json") as f:
        metrics = json.load(f)

    print("Model metrics:", json.dumps(metrics, indent=2))

    failures = [
        f"{name}={metrics[name]:.3f} < required {threshold}"
        for name, threshold in THRESHOLDS.items()
        if metrics[name] < threshold
    ]

    if failures:
        print("MODEL QUALITY GATE FAILED:")
        for f_ in failures:
            print(f"  - {f_}")
        sys.exit(1)

    print("Model quality gate passed.")


if __name__ == "__main__":
    main()
