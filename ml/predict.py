"""Inference-time wrapper around the trained XGBoost classifier.
Loads artifacts once (module-level singleton) so the FastAPI gateway pays the
deserialization cost a single time at startup, not per-request.
"""
import os
import joblib
import xgboost as xgb

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

_model = None
_feature_builder = None


def _load():
    global _model, _feature_builder
    if _model is None:
        _model = xgb.XGBClassifier()
        _model.load_model(os.path.join(ARTIFACT_DIR, "xgb_model.json"))
        _feature_builder = joblib.load(os.path.join(ARTIFACT_DIR, "feature_builder.joblib"))
    return _model, _feature_builder


def score(text: str) -> float:
    """Returns P(malicious) in [0, 1]. Returns 0.0 if artifacts are missing
    (e.g. model not yet trained) so the gateway degrades to regex-only
    detection rather than crashing."""
    try:
        model, fb = _load()
    except FileNotFoundError:
        return 0.0
    X = fb.transform([text])
    return float(model.predict_proba(X)[0, 1])
