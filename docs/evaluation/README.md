# Evaluation

Hand-labeled gold cases live in `data/gold/cases.jsonl` (24 seed jobs across
software, finance, engineering, cybersecurity, healthcare, education,
marketing, HR, sales, legal, logistics, design, and procurement;
12 dev / 12 test splits). Each case lists expected canonical skills with
importance and minimum years of experience.

Run the deterministic extractor against the gold set (no LLM quota spent):

```bash
cd backend
uv run python -m scripts.eval
# or: make eval  (from repo root; writes docs/evaluation/results.json)
```

Metrics: skill micro precision/recall/F1 (canonical-name match),
required/preferred accuracy on matched skills, evidence validity
(share of predicted skills with a valid verbatim quote), and experience
MAE in years.

Baseline (deterministic extractor, 24 cases): precision 0.75, recall 1.00,
F1 0.85, importance accuracy 0.99, evidence validity 1.00, experience
MAE 0.0. Precision is below 1.0 because the extractor surfaces every
taxonomy skill mentioned in an ad, while gold labels list only the
salient requirements. Expand the gold set (target: 80 ads per PLAN.md
§10) before treating these numbers as a quality gate.
