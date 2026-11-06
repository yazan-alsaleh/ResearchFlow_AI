# Evaluation

Hand-labeled gold cases live in `data/gold/cases.jsonl` (24 English seed
jobs across software, finance, engineering, cybersecurity, healthcare,
education, marketing, HR, sales, legal, logistics, design, and procurement;
12 dev / 12 test splits) plus `data/gold/cases-arabic.jsonl` (6 Arabic ads,
3 dev / 3 test). Each case lists expected canonical skills with importance
and minimum years of experience. Metrics are also reported per language
(`by_language` in results.json).

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

Baseline (deterministic extractor, 30 cases): precision 0.79, recall 1.00,
F1 0.88, importance accuracy 0.98, evidence validity 1.00, experience
MAE 0.0. English (24 cases): F1 0.85 — precision is below 1.0 because the
extractor surfaces every taxonomy skill mentioned in an ad, while gold
labels list only the salient requirements. Arabic (6 cases): F1 1.00,
importance accuracy 0.94 — deterministic Arabic alias mapping works, but
the Arabic gold set is small (PLAN target: 20 Arabic ads) and importance
cues are heuristic. Expand both gold sets before treating these numbers
as a quality gate.
