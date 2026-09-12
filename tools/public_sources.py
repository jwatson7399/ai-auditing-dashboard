"""Label-based public leaderboard extraction. No API key or model-generated data."""
from collections import Counter
import datetime as dt
import json
import os
import re

AA_URL = "https://artificialanalysis.ai/leaderboards/models"
ARENA_URLS = {"text": "https://arena.ai/leaderboard/text", "webdev": "https://arena.ai/leaderboard/code"}
ELO_RANGE = (800, 2000)
PUBLIC_METRICS = ("gdpval", "omni", "nohalluc")
AA_COLUMNS = {
    "gdpval": "GDPval-AA v2\nAgentic Real-World Work Tasks, (Elo-500)/2000",
    "omni": "AA-Omniscience Accuracy\nKnowledge",
    "nohalluc": "AA-Omniscience Non-Hallucination Rate\n1 - Hallucination Rate",
    "cost": "Cost per Task\nUSD",
}


def compact(s):
    return " ".join(s.split()).casefold()


def table_rows(page):
    return page.evaluate("""() => Array.from(document.querySelectorAll('table tr')).map(tr =>
        Array.from(tr.querySelectorAll('td,th')).map(td => td.innerText.trim()))""")


# Read only the metadata row adjacent to the leaderboard heading. Never use body dates.
ARENA_HEADER_JS = """() => {
    const headings = [...document.querySelectorAll('h1')];
    if (headings.length !== 1) return {heading: '', metadata: []};
    const h = headings[0];
    const row = h.parentElement?.nextElementSibling;
    return {heading: h.innerText, metadata: row ? [...row.children].map(e => e.innerText.trim()) : []};
}"""


def arena_source_date(header):
    cells = header.get("metadata", [])
    if not any(re.fullmatch(r"[\d,]+ votes", c) for c in cells) or not any(
            re.fullmatch(r"[\d,]+ models", c) for c in cells):
        return None
    dates = [c for c in cells if re.fullmatch(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4}", c)]
    if len(dates) == 1:
        try:
            return dt.datetime.strptime(dates[0], "%b %d, %Y").date().isoformat()
        except ValueError:
            pass
    return None


def fetch_public_table(url, root, name, expand=False):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until="networkidle" if expand else "domcontentloaded", timeout=90000)
            if response and response.status >= 400:
                raise RuntimeError(f"{name}: HTTP {response.status}")
            if expand:
                page.get_by_role("button", name="Expand columns", exact=True).click(timeout=30000)
                page.get_by_role("button", name="Collapse columns", exact=True).wait_for(timeout=30000)
                page.wait_for_function("""() => Array.from(document.querySelectorAll('th,td')).some(c =>
                    c.innerText.startsWith('AA-Omniscience Non-Hallucination Rate'))""", timeout=30000)
            page.locator("table tbody tr").first.wait_for(timeout=30000)
            # Wait for labeled headers as well as rows; hydration can initially leave empty cells.
            page.wait_for_function("""() => Array.from(document.querySelectorAll('table tr')).some(tr =>
                Array.from(tr.querySelectorAll('td,th')).some(c => c.innerText.trim() === 'Model'))""", timeout=30000)
            body = page.inner_text("body")
            payload = {"url": page.url, "title": page.title(), "rows": table_rows(page),
                       "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "source_updated": None}
            if "arena.ai" in url:
                header = page.evaluate(ARENA_HEADER_JS)
                payload["heading"] = header["heading"]
                payload["source_updated"] = arena_source_date(header)
            raw_dir = os.path.join(root, "data", "raw")
            os.makedirs(raw_dir, exist_ok=True)
            with open(os.path.join(raw_dir, name + "-probe.txt"), "w") as f:
                f.write(body)
            with open(os.path.join(raw_dir, name + "-table.json"), "w") as f:
                json.dump(payload, f, indent=2)
            return payload
        except Exception:
            raw_dir = os.path.join(root, "data", "raw")
            os.makedirs(raw_dir, exist_ok=True)
            try:
                with open(os.path.join(raw_dir, name + "-failure.txt"), "w") as f:
                    f.write(page.inner_text("body", timeout=5000))
            except Exception:
                pass
            raise
        finally:
            browser.close()


def labeled_rows(rows, allow_duplicates=False):
    headers = [r for r in rows if any(compact(c) == "model" for c in r)]
    if len(headers) != 1:
        raise ValueError("Expected exactly one table header with Model")
    header = headers[0]
    names = [compact(c) for c in header]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate column labels")
    mi = names.index("model")
    data = [r for r in rows[rows.index(header) + 1:] if any(r)]
    if any(len(r) != len(header) for r in data):
        raise ValueError("Table row width changed")
    model_names = [r[mi].split("\n")[0] for r in data]
    if not allow_duplicates and len(model_names) != len(set(model_names)):
        raise ValueError("Duplicate model rows")
    return names, mi, data


def parse_aa_table(rows):
    headers, mi, data = labeled_rows(rows)
    if len(data) < 20:
        raise ValueError("AA table has fewer than 20 model rows")
    result, errors = {}, {}
    for key, label in AA_COLUMNS.items():
        try:
            ci = headers.index(compact(label))
            parsed = []
            for row in data:
                text = row[ci]
                value = None
                if text not in ("", "--", "-", "N/A"):
                    pattern = r"\$(\d+(?:\.\d+)?)" if key == "cost" else r"(\d+(?:\.\d+)?)%"
                    match = re.fullmatch(pattern, text)
                    if not match:
                        raise ValueError(f"Invalid {key} cell for {row[mi]}: {text}")
                    value = float(match[1])
                    if not 0 <= value <= (500 if key == "cost" else 100):
                        raise ValueError(f"Out-of-range {key} cell for {row[mi]}")
                parsed.append({"name": row[mi], "value": value, "display": text})
            if sum(r["value"] is not None for r in parsed) < 20:
                raise ValueError(f"Fewer than 20 numeric {key} rows")
            result[key] = parsed
        except ValueError as e:
            errors[key] = str(e)
    return result, errors


def effort_key(name):
    """Conservative join: retain effort, fallback presence, and unknown settings."""
    match = re.fullmatch(r"(.*?)\s*\(([^)]*)\)", name.strip())
    base, setting = (match[1].strip(), compact(match[2])) if match else (name.strip(), "default")
    base = re.sub(r"[^a-z0-9]+", " ", base.casefold()).strip()
    fallback = "fallback" in setting
    if "non-reasoning" in setting or setting == "none":
        level = "none"
        remainder = re.sub(r"\b(non-reasoning|none|effort|default|with|fallback)\b", "", setting)
        if re.sub(r"[\s,]+", "", remainder):
            level = setting
    else:
        level_match = re.search(r"\b(max|xhigh|high|medium|low)\b", setting)
        level = level_match[1] if level_match else setting
        if level_match:
            remainder = re.sub(r"\b(adaptive|reasoning|max|xhigh|high|medium|low|effort|default|with|fallback)\b", "", setting)
            if re.sub(r"[\s,]+", "", remainder):
                level = setting  # preserve qualifiers such as a named fallback or special harness
    # A named fallback and an unspecified default fallback are not interchangeable unless
    # they resolve to one unique API row (the caller checks uniqueness).
    return base, level, fallback


def parse_arena_table(payload, board):
    expected = {"webdev": "Code Arena | WebDev 🏆 Overall", "text": "Text Arena 🏆 Overall"}
    if payload.get("url", "").rstrip("/") != ARENA_URLS[board] or compact(payload.get("heading", "")) != compact(expected[board]):
        raise ValueError(f"Arena response is not the overall {board} board")
    headers, mi, rows = labeled_rows(payload["rows"], allow_duplicates=True)
    counts = Counter(row[mi].split("\n")[0] for row in rows)
    si = next((headers.index(h) for h in ("score", "arena score", "elo", "rating") if h in headers), None)
    if si is None:
        raise ValueError("Arena table has no Score column")
    data, excluded = {}, []
    for row in rows:
        name = row[mi].split("\n")[0]
        if counts[name] > 1:
            excluded.append({"model": name, "reason": "Duplicate model label; cannot identify configuration", "display": row[si]})
            continue
        if "AutoEval" in row[si]:
            excluded.append({"model": name, "reason": "AutoEval estimate, not human votes", "display": row[si]})
            continue
        match = re.match(r"^(\d+(?:\.\d+)?)(?=\s|[+\-]|$)", row[si])
        if not match or not ELO_RANGE[0] <= float(match[1]) <= ELO_RANGE[1]:
            raise ValueError(f"Invalid Arena score for {name}: {row[si]}")
        data[name] = round(float(match[1]))
    if len(data) < 5:
        raise ValueError("Arena table has fewer than 5 scores")
    return data, excluded
