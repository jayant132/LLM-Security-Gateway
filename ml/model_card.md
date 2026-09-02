# Model Card: Prompt-Injection XGBoost Classifier

## Intended use
Second-layer detector in the guardrail ensemble (`app/guardrails.py`), scoring
P(prompt is an injection/jailbreak attempt). Runs alongside a regex layer;
a request is blocked if either layer fires. Not intended to run standalone —
it is tuned to catch what the regex layer misses (paraphrase, obfuscation),
not to replace deterministic rule coverage.

## Training data
Synthetically generated (`ml/generate_dataset.py`): 30 malicious intent
templates (jailbreak/override/harmful-request patterns) and 30 benign
templates (everyday Q&A, coding help, writing requests), each expanded into
6 variants via randomized obfuscation transforms — character spacing,
leetspeak, Cyrillic homoglyphs, case noise, synonym substitution. 360 examples
total, 80/20 train/test split, balanced classes.

**Known limitation:** synthetic data does not capture the full diversity of
real-world attack phrasing. This is a demonstration pipeline, not a
dataset trained on production traffic — retraining on real (labeled, redacted)
traffic before production use is expected practice, not optional polish.

## Features
- Character n-gram TF-IDF (3-5 grams, `analyzer=char_wb`) — robust to
  word-level obfuscation since it doesn't rely on token boundaries.
- Hand-crafted: text length, special-char ratio, digit ratio, uppercase
  ratio, Shannon entropy, suspicious-keyword hit count, spacing-trick flag.

## Model
XGBoost (`n_estimators=200, max_depth=4, learning_rate=0.1`). Shallow trees
chosen deliberately over deep ones to reduce overfitting on a small synthetic
set; retrain with more data/estimators once real traffic is available.

## Metrics (held-out test set, see `ml/artifacts/metrics.json`)
| Metric | Value |
|---|---|
| Accuracy | 0.92 |
| Precision | 0.89 |
| Recall | 0.94 |
| F1 | 0.91 |
| ROC-AUC | 0.976 |

CI gate (`ml/check_model_quality.py`) fails the build if F1 < 0.80,
recall < 0.80, or ROC-AUC < 0.85 on retrain — a regression trap, not just a
report.

## Known evasion (found by the red-team suite, not hidden)
`redteam/probes.py::ml_evade_01` — a letter-by-letter spaced-out injection
("i g n o r e ...") is currently **not** caught. Root cause: the spacing-trick
heuristic feature only fires on runs of 2+ consecutive whitespace chars, and
single-space-per-letter text doesn't trip it, so the model under-weights it.
Documented rather than patched-and-hidden because that's the point of running
a red-team suite — it should surface real gaps. Fix path: add single-space
character spacing as its own training augmentation and re-run
`ml/train_model.py`.

## Retraining
```bash
python ml/generate_dataset.py
python ml/train_model.py
python ml/check_model_quality.py
```
