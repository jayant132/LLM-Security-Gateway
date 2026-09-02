"""Feature engineering shared by training and inference so they never drift apart.

Two feature families, concatenated:
1. Character n-gram TF-IDF (3-5 grams) — robust to spacing/leetspeak/case tricks
   because it operates below the word level.
2. Hand-crafted statistical/lexical features — cheap signals that generalize
   beyond the training vocabulary (e.g. Shannon entropy catches obfuscated/
   encoded payloads even with zero token overlap with training data).
"""
import math
import re
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

SUSPICIOUS_KEYWORDS = [
    "ignore", "disregard", "override", "bypass", "jailbreak", "dan",
    "unrestricted", "unfiltered", "system prompt", "no rules", "no restrictions",
    "developer mode", "act as", "pretend",
]


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq = {}
    for c in text:
        freq[c] = freq.get(c, 0) + 1
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def handcrafted_features(texts):
    feats = []
    for t in texts:
        length = max(len(t), 1)
        special_chars = len(re.findall(r"[^a-zA-Z0-9\s]", t))
        digits = len(re.findall(r"\d", t))
        upper = len(re.findall(r"[A-Z]", t))
        keyword_hits = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in t.lower())
        feats.append([
            length,
            special_chars / length,
            digits / length,
            upper / length,
            shannon_entropy(t),
            keyword_hits,
            1.0 if re.search(r"\s{2,}", t) or " ".join(list(t.replace(" ", ""))) == t else 0.0,  # spacing-trick flag
        ])
    return np.array(feats, dtype=float)


class FeatureBuilder:
    """Fit on training text, then transform() consistently for train + inference."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), max_features=3000, sublinear_tf=True
        )

    def fit_transform(self, texts):
        tfidf = self.vectorizer.fit_transform(texts)
        hand = csr_matrix(handcrafted_features(texts))
        return hstack([tfidf, hand]).tocsr()

    def transform(self, texts):
        tfidf = self.vectorizer.transform(texts)
        hand = csr_matrix(handcrafted_features(texts))
        return hstack([tfidf, hand]).tocsr()

    def feature_names(self):
        return list(self.vectorizer.get_feature_names_out()) + [
            "length", "special_char_ratio", "digit_ratio", "upper_ratio",
            "entropy", "keyword_hits", "spacing_trick_flag",
        ]
