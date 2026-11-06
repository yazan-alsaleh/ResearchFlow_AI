# Evaluation

Hand-labeled gold cases live in `data/gold/cases.jsonl` (8 seed jobs across
software, finance, engineering, cybersecurity, healthcare, and logistics;
4 dev / 4 test splits). Each case lists expected canonical skills with
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

Baseline (deterministic extractor, 8 cases): precision 0.51, recall 1.00,
F1 0.67, importance accuracy 0.98, evidence validity 1.00, experience
MAE 0.0. Low precision is expected: the extractor surfaces every
taxonomy skill mentioned in an ad, while gold labels list only the
salient requirements. Expand the gold set (target: 80 ads per PLAN.md
§10) before treating these numbers as a quality gate.
