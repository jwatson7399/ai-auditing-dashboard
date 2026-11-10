"""Label-based public leaderboard extraction. No API key or model-generated data."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import datetime as dt
import json
import os
import re

AA_URL = "https://artificialanalysis.ai/leaderboards/models"
ARENA_URLS = {"text": "https://arena.ai/leaderboard/text", "webdev": "https://arena.ai/leaderboard/code"}
ELO_RANGE = (800, 2000)
PUBLIC_METRICS = ("gdpval", "omni", "nohalluc")
# Legacy labels. A header that still matches one of these keeps this string as its field,
# so a case-only reprint does not look like a new score definition. Newer wording is stored
# as the header the page actually showed.
AA_COLUMNS = {
    "gdpval": "GDPval-AA v2\nAgentic Real-World Work Tasks, (Elo-500)/2000",
    "omni": "AA-Omniscience Accuracy\nKnowledge",
    "nohalluc": "AA-Omniscience Non-Hallucination Rate\n1 - Hallucination Rate",
    "cost": "Cost per Task\nUSD",
}
# A minor version ("v2", "v2.1", "v1.1") may appear after the benchmark name. Case is
# folded by compact() before these patterns run.
_VERSION = r"(?: v\d+(?:\.\d+)*)?"
AA_COLUMN_MATCHERS = {
    "gdpval": re.compile(
        rf"^gdpval-aa{_VERSION} agentic real-world work tasks, (?:\(elo-500\)/2000|elo)$"),
    "omni": re.compile(rf"^aa-omniscience{_VERSION} accuracy knowledge$"),
    "nohalluc": re.compile(
        rf"^aa-omniscience{_VERSION} non-hallucination rate 1 - hallucination rate$"),
    "cost": re.compile(r"^cost per task usd$"),
}
# Used by the browser wait as well as tests. The page may insert a version and change case.
OMNISCIENCE_NON_HALLUCINATION_HEADER = r"^AA-Omniscience(?: v\d+(?:\.\d+)*)? Non-Hallucination Rate"
# Raw GDPval Elo is converted with the formula the old column printed: (Elo-500)/2000.
# 500 Elo is 0 on that scale. Elo below 500 is a negative percentage point score.
# The sanity window only rejects cells that are not Elo-shaped numbers.
GDPVAL_ELO_ZERO = 500
GDPVAL_ELO_SANITY = (-1000, 3000)
_MISSING_CELLS = {"", "--", "-", "N/A"}
_CI_LINE = re.compile(r"^[+\-]\d+(?:\.\d+)?/[+\-]\d+(?:\.\d+)?$")


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
        page = None
        try:
            page = browser.new_page()
            response = page.goto(url, wait_until="networkidle" if expand else "domcontentloaded", timeout=90000)
            if response and response.status >= 400:
                raise RuntimeError(f"{name}: HTTP {response.status}")
            if expand:
                page.get_by_role("button", name="Expand columns", exact=True).click(timeout=30000)
                page.get_by_role("button", name="Collapse columns", exact=True).wait_for(timeout=30000)
                page.wait_for_function(
                    """pattern => Array.from(document.querySelectorAll('th,td')).some(c =>
                        new RegExp(pattern, 'i').test(c.innerText.trim()))""",
                    arg=OMNISCIENCE_NON_HALLUCINATION_HEADER, timeout=30000)
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
                if page is not None:
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


def elo_to_percent(elo):
    """(Elo - 500) / 2000 as percentage points, rounded half up to one decimal."""
    points = (Decimal(str(elo)) - Decimal(GDPVAL_ELO_ZERO)) / Decimal(2000) * Decimal(100)
    return float(points.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _header_row(rows):
    headers = [r for r in rows if any(compact(c) == "model" for c in r)]
    if len(headers) != 1:
        raise ValueError("Expected exactly one table header with Model")
    return headers[0]


def _match_column(header, key):
    names = [compact(c) for c in header]
    hits = [i for i, name in enumerate(names) if AA_COLUMN_MATCHERS[key].fullmatch(name)]
    if len(hits) != 1:
        raise ValueError(f"Expected one {key} column, found {len(hits)}")
    return hits[0]


def _cell_lines(text):
    return [ln.strip() for ln in str(text).splitlines() if ln.strip()]


def _parse_number_cell(text, key, model, kind):
    """kind is 'percent', 'dollars', or 'elo'. Missing cells return None."""
    if text in _MISSING_CELLS:
        return None, None
    lines = _cell_lines(text)
    if not lines or lines[0] in _MISSING_CELLS:
        return None, None
    if any(not _CI_LINE.fullmatch(ln) for ln in lines[1:]):
        raise ValueError(f"Invalid {key} cell for {model}: {text}")
    token = lines[0].replace(",", "").replace("\u2212", "-").replace("\u2013", "-")
    if kind == "dollars":
        match = re.fullmatch(r"\$(\d+(?:\.\d+)?)", token)
        ceiling = 500
    elif kind == "percent":
        match = re.fullmatch(r"(\d+(?:\.\d+)?)%", token)
        ceiling = 100
    else:
        match = re.fullmatch(r"-?\d+(?:\.\d+)?", token)
        ceiling = None
    if not match:
        raise ValueError(f"Invalid {key} cell for {model}: {text}")
    number = float(match.group(1) if kind != "elo" else match.group(0))
    if kind == "elo":
        if not GDPVAL_ELO_SANITY[0] <= number <= GDPVAL_ELO_SANITY[1]:
            raise ValueError(f"Out-of-range {key} cell for {model}: {text}")
        return elo_to_percent(number), number
    if not 0 <= number <= ceiling:
        raise ValueError(f"Out-of-range {key} cell for {model}")
    return number, None


def _column_cells_by_model(data, mi, ci):
    """One cell per model. Agreeing copies collapse. Disagreeing copies are not guessed."""
    grouped, order = {}, []
    for row in data:
        name = row[mi]
        if name not in grouped:
            order.append(name)
            grouped[name] = []
        grouped[name].append(row[ci])
    chosen = []
    for name in order:
        present = []
        for cell in grouped[name]:
            lines = _cell_lines(cell)
            if lines and lines[0] not in _MISSING_CELLS:
                present.append(cell.strip())
        # A second copy with a blank cell is not the same fact as a copy with a number.
        # Two blanks stay blank. Two identical numbers collapse to one.
        if len(set(present)) > 1 or (present and len(present) != len(grouped[name])):
            chosen.append((name, None))
        else:
            chosen.append((name, present[0] if present else "--"))
    return chosen


def parse_aa_table(rows):
    _headers, mi, data = labeled_rows(rows, allow_duplicates=True)
    if len({row[mi].split("\n")[0] for row in data}) < 20:
        raise ValueError("AA table has fewer than 20 model rows")
    header = _header_row(rows)
    result, errors = {}, {}
    for key in AA_COLUMNS:
        try:
            ci = _match_column(header, key)
            raw_header = header[ci]
            field = AA_COLUMNS[key] if compact(raw_header) == compact(AA_COLUMNS[key]) else raw_header
            kind = "dollars" if key == "cost" else "percent"
            if key == "gdpval" and compact(raw_header).endswith(", elo"):
                kind = "elo"
            parsed = []
            for name, cell in _column_cells_by_model(data, mi, ci):
                if cell is None:
                    value, raw_elo, display = None, None, "ambiguous"
                else:
                    value, raw_elo = _parse_number_cell(cell, key, name, kind)
                    display = cell
                item = {"name": name, "value": value, "display": display, "field": field,
                        "column_title": raw_header.split("\n")[0].strip(),
                        "scale": "percent" if key != "cost" else "usd"}
                if raw_elo is not None:
                    item["raw_elo"] = int(raw_elo) if raw_elo == int(raw_elo) else raw_elo
                parsed.append(item)
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
