from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter("gateway_requests_total", "Total chat requests")
BLOCKED_INPUT_TOTAL = Counter(
    "gateway_blocked_input_total", "Requests blocked by input guardrails", ["category", "source"]
)
OUTPUT_REDACTIONS_TOTAL = Counter(
    "gateway_output_redactions_total", "Redactions applied to model output", ["category"]
)
REQUEST_LATENCY = Histogram("gateway_request_latency_seconds", "End-to-end request latency")
ML_SCORE_DIST = Histogram(
    "gateway_ml_injection_score", "XGBoost P(malicious) score distribution",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
