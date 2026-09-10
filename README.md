# AI Auditing Dashboard

Personal AI auditing dashboard.

Benchmark Scout files new credible AI model benchmark findings into `inbox/benchmarks/` for human review. It does not rank models or write dashboard UI.

## Scout paths

- `sources/allowlist.md` — allowed sources (authority)
- `inbox/benchmarks/seen.md` — already-filed items
- `inbox/benchmarks/YYYY-MM-DD.md` — one report per daily run
- `tests/fixtures/` — test fixtures only. Never read by the Scout, Verifier, or dashboard rebuild. Files here may contain deliberately incorrect items and must never be used as data.
- `log/runs-*.csv` — append-only run log, one file per writer, one line per run. Header `date,time_et,agent,status,items,pr,notes`. Notes never contain a comma. Acceptance-test runs against anything under `tests/` get no log line.
- `log/run-log.xlsx` — generated from the CSVs by the daily rebuild, one tab per agent plus a combined tab. Generated output; never hand-edited.

## Daily rebuild

`tools/rebuild.py` runs on GitHub Actions (`.github/workflows/rebuild.yml`) at 8:15am ET and builds the dashboard from structured sources and the merged inbox on `main`. No language model touches a number. It writes:

- `data/YYYY-MM-DD.json` and `data/latest.json`: every number on the page, with source, fetch date, and effort setting
- `data/raw/aa-llms-latest.json`: the last Artificial Analysis API response, overwritten daily
- `site/index.html`: the page, built from `site/template.html`, served by GitHub Pages
- `log/run-log.xlsx`: generated from the run log CSVs
- one line in `log/runs-rebuild.csv`, even when the run fails

The Artificial Analysis key lives in the repository's Actions secrets as `AA_API_KEY` and nowhere else. Data from Artificial Analysis is used under its attribution requirement.

Unresolved entries in `inbox/proposed-sources.md` (domains on neither the allowlist nor the Blocklist) are shown on the page with the Verifier's recorded facts and no recommendation; the decision is a human edit to `sources/allowlist.md`.

`inbox/commentary/YYYY-MM-DD.md` is written by the Commentator agent from the day's JSON. A pull request carrying the `commentary` label and touching only that path is merged by `.github/workflows/commentary-merge.yml`, which then rebuilds the page. Every number in the commentary is checked against the day's data; a block with a number not in the data is set aside and the page shows the templated line instead, marked.

### Open question: cost per task

The efficiency table shows a list price per million tokens, not a cost per task. The free Artificial Analysis tier does not publish cost per task: it varies with effort setting and needs per-run token counts, which the API does not expose. The only price it gives, `price_1m_blended_3_to_1`, is identical at every effort setting of a model. The two equivalence blocks that once said "X% less per task" have been removed rather than left dividing that price by itself.

This leaves principle 6 partly unmet. Two ways to close it, neither taken yet: pay for the tier that exposes per-task cost, or scrape the leaderboard page for that one column. Speed and wait still vary with effort and are unaffected.

### Benchmarks the API does not carry

`gdpval`, `omni`, `nohalluc` and `gdppdf` have no field on this tier. They are carried forward from the previous day and marked stale rather than guessed at, so a blend that depends on one of them is scored on the tests that are present.
