"""Guardrail engine: input (prompt injection / PII) + output (leak / toxicity) checks.
Maps each rule to its OWASP LLM Top 10 category for reporting.

Input detection is a two-layer ensemble:
  1. Regex/heuristic layer  - fast, deterministic, catches known patterns.
  2. XGBoost ML layer       - catches paraphrased/obfuscated attacks that
                              slip past static rules (see ml/predict.py).
A request is blocked if EITHER layer fires. This mirrors how production
guardrail systems (Lakera Guard, NeMo Guardrails) actually work: static
rules for cheap deterministic coverage, an ML classifier for generalization.
"""
import re

from ml.predict import score as ml_score
from app.metrics import ML_SCORE_DIST

ML_THRESHOLD = 0.6

INJECTION_PATTERNS = [
    (r"ignore (all |any |previous |above |prior )*instructions", "LLM01_PROMPT_INJECTION"),
    (r"you are now (dan|jailbroken|unrestricted)", "LLM01_PROMPT_INJECTION"),
    (r"disregard (the )?(system|previous) prompt", "LLM01_PROMPT_INJECTION"),
    (r"pretend (you|to) (are|be) .* no (rules|restrictions)", "LLM01_PROMPT_INJECTION"),
    (r"reveal (your|the) (system prompt|instructions)", "LLM01_PROMPT_INJECTION"),
    (r"</?(system|admin|root)>", "LLM01_PROMPT_INJECTION"),
    (r"base64:|decode this:", "LLM01_PROMPT_INJECTION"),
]

PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "LLM06_SENSITIVE_INFO_DISCLOSURE", "[REDACTED_SSN]"),
    (r"\b\d{16}\b|\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b", "LLM06_SENSITIVE_INFO_DISCLOSURE", "[REDACTED_CARD]"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "LLM06_SENSITIVE_INFO_DISCLOSURE", "[REDACTED_EMAIL]"),
    (r"\b(sk|api|key)[-_][a-zA-Z0-9]{16,}\b", "LLM02_INSECURE_OUTPUT_HANDLING", "[REDACTED_SECRET]"),
]

TOXIC_KEYWORDS = ["kill yourself", "make a bomb", "how to hack into", "child sexual"]


def check_input(text: str):
    """Returns (blocked: bool, reasons: list[dict]). reasons include a
    'source' field ('regex' or 'ml') so callers/metrics can tell which
    layer caught the attack."""
    reasons = []
    lower = text.lower()
    for pattern, category in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            reasons.append({"rule": pattern, "category": category, "source": "regex"})
    for kw in TOXIC_KEYWORDS:
        if kw in lower:
            reasons.append({"rule": f"toxic_keyword:{kw}", "category": "LLM09_OVERRELIANCE_HARMFUL_CONTENT", "source": "regex"})

    ml_p = ml_score(text)
    ML_SCORE_DIST.observe(ml_p)
    if ml_p >= ML_THRESHOLD:
        reasons.append({
            "rule": f"xgboost_classifier(p={ml_p:.3f})",
            "category": "LLM01_PROMPT_INJECTION",
            "source": "ml",
        })

    return (len(reasons) > 0, reasons)


def check_output(text: str):
    """Redacts sensitive info in model output. Returns (redacted_text, reasons)."""
    reasons = []
    redacted = text
    for pattern, category, placeholder in PII_PATTERNS:
        if re.search(pattern, redacted):
            reasons.append({"rule": pattern, "category": category})
            redacted = re.sub(pattern, placeholder, redacted)
    return redacted, reasons
