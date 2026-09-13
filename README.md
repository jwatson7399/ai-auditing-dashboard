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

`tools/rebuild.py` runs on GitHub Actions (`.github/workflows/rebuild.yml`) on a best-effort 12:15 UTC schedule (8:15am ET during daylight time) and builds the dashboard from structured sources and the merged inbox on `main`. No language model touches a number. It writes:

- `data/YYYY-MM-DD.json` and `data/latest.json`: every number on the page, with source, fetch date, and effort setting
- `data/raw/aa-llms-latest.json`: the last Artificial Analysis API response, overwritten daily
- `site/index.html`: the page, built from `site/template.html`, served by GitHub Pages
- `log/run-log.xlsx`: generated from the run log CSVs
- one line in `log/runs-rebuild.csv`, even when the run fails

The Artificial Analysis key lives in the repository's Actions secrets as `AA_API_KEY` and nowhere else. Data from Artificial Analysis is used under its attribution requirement.

Unresolved entries in `inbox/proposed-sources.md` (domains on neither the allowlist nor the Blocklist) are shown on the page with the Verifier's recorded facts and no recommendation; the decision is a human edit to `sources/allowlist.md`.

`inbox/commentary/YYYY-MM-DD.md` is written by the Commentator agent from the day's JSON. A non-draft pull request into `main` carrying the `commentary` label and touching only dated commentary files and/or `log/runs-commentator.csv` is merged by `.github/workflows/commentary-merge.yml`. Events for each PR are serialized, then its live state and head are checked. Only a merge that changes commentary dispatches a rebuild; a log-only update does not. Already-closed PRs do nothing. Every number in the commentary is checked against the day's data; a block with a number not in the data is set aside and the page shows the templated line instead, marked.

### Public leaderboard sources

The rebuild renders the public Artificial Analysis models table, expands its columns, and matches exact header labels and units. GDPval-AA v2 uses the displayed `(Elo-500)/2000` scale, expressed as percentage points. AA-Omniscience Accuracy and Non-Hallucination Rate use their separate percent columns. Non-hallucination is the complement of AA's conditional hallucination measure, not the percentage of all responses that are correct. GDP.pdf remains carried forward and labeled stale until a separate source is verified.

Cost per task comes from the same public table and is joined to API rows by model, effort level, and fallback presence. Ambiguous or unknown settings are left unjoined and logged. Original names and join keys are stored with each cost. A displayed $0.00 is retained as rounded and excluded from savings comparisons; it is not interpreted as free. Missing values stay unavailable or carry forward with their original date. The separate token-price column remains available.

The WebDev fetch uses `https://arena.ai/leaderboard/code`, the overall WebDev board. It preserves the board's published date separately from the fetch date. AutoEval estimates are recorded as exclusions and do not enter the human-vote blend. A source change is not automatically called a re-grade.

Raw rendered text and table rows are saved under `data/raw/`. Benchmarks retain per-model provenance, effort settings, and dates; rows absent from a successful fetch are preserved separately as historical observations and excluded from current rankings. A whole-source outage retains the last available board with stale dates. A failed column leaves other validated columns usable. Task cards warn when their blend includes stale scores.

The three public metrics remain owned by their validated public columns, even if similarly named API fields appear later. Changes in source, field, scale, board or index version reset numeric comparisons. Arena dates are read only from the metadata row beside the leaderboard heading.

### Open question: long-term cost source

The public-table scrape implements the September 10 decision. Revisit a paid API tier or removing the cost column after operational experience. Public pages can change; parse failures are logged and stale values remain visible. Model and effort comparisons use only fresh positive costs, so unavailable or rounded-zero prices cannot produce savings claims.

### Validation

Run `python -m unittest discover -s tests -p 'test_*.py'`. The source checks can run without an AA key. Full production fetching still requires `AA_API_KEY` in Actions; never place it in local files. Test output must not be committed as production data or appended to merged run logs.

### Morning readiness and recovery

GitHub scheduled workflows can arrive late. On September 11 and 12, 2026 the daily scheduled runs were created at 12:24 PM and 11:28 AM ET, respectively. Both mornings the Commentator reported missing daily data. The configured cron does not establish a before-9-AM delivery guarantee. GitHub documents this limitation in [scheduled workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

After this change is merged, the external Commentator's first step should run the following from a checkout of current `main`, with an authenticated `gh` account allowed to dispatch Actions:

```sh
python tools/delivery.py ensure-data > /tmp/auditor-commentator-data.json
```

Only use the output after exit status 0. It is today's dated JSON read from `main`, never a local preview. Retrieval uses GitHub's raw media type, which supports files up to 100 MB and avoids the JSON content envelope's 1 MB limit; directory listing and API errors remain separate from a missing daily file. See [GitHub's Contents API limits](https://docs.github.com/en/rest/repos/contents#get-repository-content). An `ok` or `partial` snapshot with picks and at least one non-stale benchmark fetched today is usable; missing GDP.pdf or costs still retain their existing warnings. Missing, yesterday-only, or entirely carried-forward data triggers one authenticated recovery dispatch. The command polls for up to ten minutes, plus bounded API-call time, and fails if data is still unavailable. API/authentication errors fail immediately instead of triggering speculative rebuilds. A failure must produce a blocked report, not commentary from yesterday's numbers. Inspect the Actions run and retry explicitly if necessary.

Recovery uses the `ensure_daily` workflow input. The existing workflow lock serializes rebuilds, and a check after checkout skips fetching and committing when today's usable snapshot already equals `latest.json`. Delayed scheduled runs use this same check. Explicit manual refreshes and commentary publications still rebuild by default. Reused data still uploads and deploys the committed page so a previous Pages failure can recover. The helper establishes data readiness on `main`, not successful Pages delivery.

A saved Grok Bot brief was located outside the worktree. It specifies 8:45 AM ET and a credential that cannot dispatch workflows; the live settings remain unverified. [The rollout proposal](docs/commentator-recovery-rollout.md) provides exact prompt replacements, an 8:25 AM ET schedule proposal, and a separate recovery-credential requirement. Applying and verifying those changes remains a rollout prerequisite; validate the next actual morning end to end. The UTC cron is unchanged and still requires a daylight-saving adjustment in November.

If commentary merges but the explicit dispatch fails, the merge workflow fails visibly. Re-running a closed PR event intentionally does nothing; recover with `gh workflow run rebuild.yml --ref main`. Do not use `--no-fetch` as a commentary publication shortcut: that option has separate carry-forward semantics.
