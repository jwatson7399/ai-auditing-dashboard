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

`inbox/commentary/YYYY-MM-DD.md` is written by the Commentator agent from the day's JSON. A pull request carrying the `commentary` label and touching only that path is merged by `.github/workflows/commentary-merge.yml`, which then rebuilds the page. Every number in the commentary is checked against the day's data; a block with a number not in the data is set aside and the page shows the templated line instead, marked.
