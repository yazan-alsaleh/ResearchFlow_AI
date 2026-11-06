# Seed corpus provenance

`jobs.jsonl` and `skills.json` are **sample fixtures**, written for local development and the
public demo. They are not scraped from live job boards and they are not a census of the Qatar
labor market.

## What is in the corpus

- 24 cross-sector job ads (software/data, finance, engineering, marketing, HR, healthcare,
  education, sales, administration, legal, logistics, project management, business, design,
  customer service, operations, procurement).
- Company names are real Qatari organizations, but the ads, salary ranges, and URLs are
  illustrative. URL paths use a `seed=` parameter that is stripped during canonicalization.
- Skill aliases are a curated taxonomy of about 200 skills covering technical, certification,
  non-technical, and soft-skill categories.

## Why fixtures

The product claim is not “we scraped the internet.” The claim is that the pipeline is
evidence-backed end to end. A small, controlled corpus makes every step reviewable:

1. The deterministic extractor can be checked against the ad text.
2. The evidence pack can be recomputed by hand.
3. The report validator can be tested against known-good and known-bad claims.

## Replacing the fixtures

Live collection will be added as source adapters. Each adapter must record:

- the source's robots.txt URL and terms URL,
- the policy decision and review date,
- crawl delay and maximum request rate,
- attribution requirements,
- a fetch log with status codes, content hashes, and durations.

Do not add a source that disallows automated access, requires authentication, or prohibits
redistribution of listing text without permission.

## Attribution

Company names are used only to describe sample scenarios. Reports generated from this corpus are
labeled as snapshots and must not be presented as live market measurements.
