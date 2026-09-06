# Verifier report: 2026-09-06
checked_file: tests/fixtures/verifier-test-2026-09-06.md
run_time: 2026-09-06 15:58 ET
items_checked: 10
passed: 4
failed: 6
unverifiable: 0

## Verdicts

### Item 1
verdict: pass
reason: all checks passed

### Item 2
verdict: pass
reason: all checks passed

### Item 3
verdict: fail_quote
reason: quote has Sol at 28.7% but page has 28.2%; also fail_score (score field 28.7% vs page 28.2%)
found: "OpenAI leads GDP.pdf with GPT-6 Astra at 33.2% and GPT-5.6 Sol at 28.2%, followed by Claude Fable 5.1 at 26.2%"

### Item 4
verdict: fail_quote
reason: quote is a paraphrase, not word-for-word; also fail_score (57 not on this page); also fail_settings (Adaptive Reasoning, Max Effort, Default Fallback not on this page)
found: "Anthropic’s Claude Fable 5.1 leads the Index, followed by OpenAI’s GPT-6 Astra, which shows a 4pt gain over GPT-5.6 Sol."

### Item 5
verdict: fail_link
reason: url returns 404 Not Found

### Item 6
verdict: fail_quote
reason: quoted sentence does not appear word-for-word on the page; also fail_source (cryptobriefing.com is on the Blocklist)
found: "OpenAI’s Astra just posted a 169 on the Epoch Capabilities Index, the composite benchmark maintained by independent research organization Epoch AI."

### Item 7
verdict: fail_settings
reason: settings facts "5 repeats" and "tools enabled" do not appear on the cited page; no second url in notes

### Item 8
verdict: pass
reason: all checks passed

### Item 9
verdict: fail_quote
reason: quote "kimi-k3-max 1674" not on page; also fail_score (page shows 1489±5); also fail_source (arena.ai is not listed on the allowlist; LMArena entry is lmarena.ai)
found: "kimi-k3-max Moonshot · Kimi K3 license | 1489±5"

### Item 10
verdict: pass
reason: all checks passed