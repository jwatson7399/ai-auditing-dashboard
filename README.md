# AI Auditing Dashboard

Personal AI auditing dashboard.

Benchmark Scout files new credible AI model benchmark findings into `inbox/benchmarks/` for human review. It does not rank models or write dashboard UI.

## Scout paths

- `sources/allowlist.md` — allowed sources (authority)
- `inbox/benchmarks/seen.md` — already-filed items
- `inbox/benchmarks/YYYY-MM-DD.md` — one report per daily run
- `tests/fixtures/` — test fixtures only. Never read by the Scout, Verifier, or dashboard rebuild. Files here may contain deliberately incorrect items and must never be used as data.
