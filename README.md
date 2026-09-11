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

### Public leaderboard sources

The rebuild renders the public Artificial Analysis models table, expands its columns, and matches exact header labels and units. GDPval-AA v2 uses the displayed `(Elo-500)/2000` scale, expressed as percentage points. AA-Omniscience Accuracy and Non-Hallucination Rate use their separate percent columns. Non-hallucination is the complement of AA's conditional hallucination measure, not the percentage of all responses that are correct. GDP.pdf remains carried forward and labeled stale until a separate source is verified.

Cost per task comes from the same public table and is joined to API rows by model, effort level, and fallback presence. Ambiguous or unknown settings are left unjoined and logged. Original names and join keys are stored with each cost. A displayed $0.00 is retained as rounded and excluded from savings comparisons; it is not interpreted as free. Missing values stay unavailable or carry forward with their original date. The separate token-price column remains available.

The WebDev fetch uses `https://arena.ai/leaderboard/code`, the overall WebDev board. It preserves the board's published date separately from the fetch date. AutoEval estimates are recorded as exclusions and do not enter the human-vote blend. A source change is not automatically called a re-grade.

Raw rendered text and table rows are saved under `data/raw/`. Benchmarks retain per-model provenance, effort settings, and dates; rows absent from a later fetch carry forward marked stale. A failed column leaves other validated columns usable. Task cards warn when their blend includes stale scores.

### Open question: long-term cost source

The public-table scrape implements the September 10 decision. Revisit a paid API tier or removing the cost column after operational experience. Public pages can change; parse failures are logged and stale values remain visible. Model and effort comparisons use only fresh positive costs, so unavailable or rounded-zero prices cannot produce savings claims.

### Validation

Run `python -m unittest discover -s tests -p 'test_*.py'`. The source checks can run without an AA key. Full production fetching still requires `AA_API_KEY` in Actions; never place it in local files. Test output must not be committed as production data or appended to merged run logs.
