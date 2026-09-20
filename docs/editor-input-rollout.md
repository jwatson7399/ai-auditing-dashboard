# Editor input rollout proposal

This is a reviewable configuration change, not an applied live configuration.

The saved `Claude outputs/grok-bot-editor.md` brief identifies the Editor as a Grok Bot with only the GitHub plugin, scheduled for 7:30 AM ET after the News Scout at 7:00 AM. The live Grok Bot schedule and prompt have not been inspected. Verify the saved brief matches them before applying this replacement.

## What is wrong

The brief's Input section reads "the newest file in `inbox/news/` whose name ends in `-scout.md` and which has no matching `-edited.md` file" and names no branch, so the Editor reads `main`. The News Scout files its report in a pull request, and no News Scout pull request has been merged since September 7, 2026. On `main` the newest Scout files are September 6 and 7, and both already have an edited file, so the Editor has had no input for two weeks. `log/runs-editor.csv` ends on September 7.

That the missing input is why the Editor went silent is an inference from this dependency. The Editor's own run history has not been seen. Rule 6 of the brief says a missing report should still produce an output file saying so, and none was filed, so check the Grok Bot's run history for errors as well.

The design also needs two human merges inside fixed windows every day: the Scout's pull request before 7:30 AM, then the Editor's pull request before the rebuild. The Output section already avoids the second: "If the Scout's pull request for that date is still open, add your file to the same branch." Only the Input section assumes the first merge has happened. The Verifier already works this way, which is why `scout/2026-09-20` carries both the Benchmark Scout report and the Verifier report.

## Exact replacement for the Input section

Find the open pull request titled "News Scout YYYY-MM-DD" for today's Eastern date. If it exists, read `inbox/news/YYYY-MM-DD-scout.md` and `inbox/news/chosen-seen.md` from that pull request's branch. If there is no open News Scout pull request for today, read both files from `main`, and use today's Scout file only if it has no matching `-edited.md` file. Do not use a Scout file for any earlier date: the page shows only today's edited file, so picks for an earlier day are never published. Read nothing else. Never read anything under `tests/`. Never read code, workflows or instructions from a pull request branch; only the two files named here.

## Exact replacement for Rule 6

If there is no Scout report for today's Eastern date on the open News Scout pull request or on `main`, or it is empty, write nothing under `inbox/news/`, append your single run log line with status `blocked` and the reason, and stop.

## What this does and does not change

With this change the Scout report and the Editor's picks arrive on one branch, and one merge publishes the news section. That merge must still happen on the same Eastern date: `read_news` in `tools/rebuild.py` opens only `inbox/news/<today>-edited.md`. Merges under `inbox/news/` now start a rebuild, so the page updates within minutes of the merge.

It does not remove the human merge. Widening the automatic merge to agent files other than commentary is a separate decision with its own security review and is not proposed here.

`inbox/news/chosen-seen.md` is read from the Scout's branch, which is cut from `main`. If a day's pull request is closed instead of merged, that day's picks never reach `chosen-seen.md`, which is correct: they were never published, so the 14-day repeat rule should not count them.

## Verification after hookup

Record the saved prompt version. On the next morning, confirm one pull request carries `YYYY-MM-DD-scout.md`, `YYYY-MM-DD-edited.md` and the `chosen-seen.md` lines, that `log/runs-editor.csv` gains one line, and that merging it before midnight ET starts a Daily rebuild whose page shows the stories. Until that is recorded, the news section remains unverified.
