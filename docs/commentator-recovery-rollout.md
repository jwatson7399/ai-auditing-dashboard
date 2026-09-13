# Commentator recovery rollout proposal

This is a reviewable configuration change, not an applied live configuration.

The saved `Claude outputs/grok-bot-commentator.md` brief identifies the Commentator as a Grok Bot, scheduled for 8:45 AM ET. Its token is restricted to repository contents and pull requests and explicitly cannot run workflows. Its Input section waits ten minutes for a missing daily file, retries once, then logs blocked. The live Grok Bot schedule, prompt, runner and credential configuration have not been inspected. Verify the saved brief matches them before applying these replacements.

## Setup changes after PR 38 review and merge

1. Change the existing Commentator schedule from 8:45 AM to **8:25 AM America/New_York**, daily. Preserve the existing task rather than creating a duplicate. This provides 35 minutes for recovery, writing, merge and deployment; it is a proposed allowance, not a delivery guarantee. Keep the GitHub daily cron unchanged in this batch.
2. Keep the existing commentary-writing credential unchanged. Provision a separate recovery credential restricted to this repository, with **Contents: read** and **Actions: write**. Expose it to the runner as `AUDITOR_RECOVERY_TOKEN`, only for the readiness command. Do not paste it into the prompt or repo. Actions write permits more than a single workflow; review that permission explicitly. Do not grant Workflows write or access to secrets. If separate credentials are unsupported by the runner, stop and resolve that deployment constraint rather than silently broadening its existing token.
3. Ensure the runner has Python 3.9+ with America/New_York timezone data, `gh`, network access to GitHub, and a checkout refreshed from trusted `main` before each run. Execute `tools/delivery.py` from that checkout, never a proposed PR branch. The saved brief establishes gh use, but does not establish this Python/checkout capability; verify it.
4. Replace the Input section's first bullet and add the execution exception below. Preserve other editorial rules and the single daily log-line rule.

## Exact replacement for the first Input bullet

Before writing, run the trusted main checkout's `tools/delivery.py ensure-data` command with the recovery credential. It reads only today's dated JSON from main as editorial input, and can request the authenticated Daily rebuild when today's usable data is absent. It does not fetch benchmark sources locally.

From the current-main checkout, use a unique temporary directory:

```sh
task_dir=$(mktemp -d)
GH_TOKEN="${AUDITOR_RECOVERY_TOKEN:?Recovery credential is not configured}" \
  python3 tools/delivery.py ensure-data > "$task_dir/today.json"
```

Proceed only when the command exits 0. Read `today.json` from that temporary directory as today's authoritative input, checking its date against today's Eastern date. Use its `previous_date` to read the comparison file from main as before. Do not treat a created or nonempty output file as success without checking exit status. Do not expose credentials in messages, logs or output.

If the command fails for any reason, including missing credentials, API errors, timeout or date rollover, write nothing under `inbox/` and append the existing single blocked log line with a concise reason. Do not fall back to yesterday or repeatedly dispatch recovery. Inspect Actions before an explicit retry. Normal GDP.pdf and cost gaps can leave status partial; readiness does not mean every source is fresh.

## Exact execution exception to Rules 6 and 8

You may execute `tools/delivery.py` from the runner's trusted main checkout and create temporary files outside the repository to receive its output. This is an execution exception, not an additional source of editorial information. You may use the recovery credential only for this command. All repository edit restrictions remain: only today's commentary and your append-only run log may change. Never read test fixtures or proposed PR code as data.

## Publication wording replacement

Replace the sentence “That message is how the reader learns the page is ready” in Notification with: “Opening the PR means commentary was submitted for publication. Do not say the live page is ready until merge and Pages deployment have been independently confirmed.” The readiness helper confirms data on main, not live deployment. Preserve the existing headline, eight picks and link format, and identify it as submitted commentary.

## Verification after hookup

Record the actual saved schedule, prompt version and credential permission names, never the credential. Test the command's already-ready path first. A missing-data recovery test must be deliberate and observed, not created by deleting production data. The next naturally missing morning can exercise that path; mocks already cover failure handling.

Observe a real morning: start near 8:25 ET, usable current-date JSON before prose, one commentary PR/log entry, one publication dispatch, green Pages deployment and a matching live stamp/data before 9 AM. A log-only blocked PR must not dispatch a refresh. The later scheduled run may reuse data and deploy without another fetch. If merge succeeds but publication dispatch fails, manually dispatch rebuild.yml; a closed-PR event rerun does nothing.

Until those checks are recorded, the before-9-AM goal remains unverified. If the live task cannot be accessed, the exact missing access is its Grok Bot schedule/prompt editor and runner environment/credential configuration. This document is sufficient to make those edits reviewable, but does not claim they were applied.
