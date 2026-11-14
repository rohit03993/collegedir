"""Read one saved CollegeDekho college folder into facts and tables.

The HTML files live under the CollegeDekho data folder. This module does not
download anything.
"""

import re
from pathlib import Path

from lxml import html as lhtml

SOURCE = Path(r"F:\Rohit Development\admission setu\college-dekho\data\colleges")
PAGES = ("courses", "admission", "placement", "cutoff", "scholarship")
SKIP_HEADING = re.compile(
    r"review|rating|feedback|share your|similar college|student preferred|"
    r"related question|explore more|table of contents|top courses at|"
    r"faqs|some faqs|by degree|by specialization|by course|related news|"
    r"expired events|kya hai|\?",
    re.I,
)
LABEL = re.compile(
    r"course|fee|rank|year|categor|eligib|duration|seat|package|particular|"
    r"statistic|event|date|program|exam|score|round|amount|name|scheme|sector|title",
    re.I,
)
FEE_OK = re.compile(r"\d,\d{2},\d{3}|\d{5,}|lakh|lac|inr|₹", re.I)


def clean(value):
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) > 500:
        return text[:484] + " [truncated]"
    return text


def usable_fee(value):
    text = clean(value)
    if text and FEE_OK.search(text):
        return text
    return None


def usable_exams(value):
    text = re.sub(r"^NIRF Ranking\s+", "", clean(value), flags=re.I)
    if not text or text.lower() == "nirf ranking":
        return None
    return text


def table_record(page, heading, rows):
    if SKIP_HEADING.search(heading or ""):
        return None
    header = rows[0]
    body = rows[1:]
    if len(header) < 2:
        return None
    if not any(LABEL.search(cell) for cell in header):
        names = [cell for cell in header if cell]
        if len(names) < 3:
            return None
        return {
            "page": page,
            "heading": heading or None,
            "columns": ["Name"],
            "rows": [[name] for name in names],
        }
    if not body:
        return None
    width = len(header)
    kept = []
    for row in body:
        if len(row) != width or not any(row):
            continue
        kept.append(row)
        if len(kept) >= 80:
            break
    if not kept:
        return None
    return {
        "page": page,
        "heading": heading or None,
        "columns": header,
        "rows": kept,
    }


def parse_page(folder, page):
    path = folder / f"{page}.html"
    if not path.exists():
        return []
    try:
        document = lhtml.fromstring(path.read_bytes())
    except Exception:
        return []
    nodes = document.xpath("//*[contains(@class,'collegeDetailMainContainer')]")
    root = nodes[0] if nodes else document
    records = []
    heading = ""
    for node in root.iter():
        if node.tag in {"h2", "h3"}:
            heading = clean(" ".join(node.itertext()))
            continue
        if node.tag != "table" or node.xpath("ancestor::table"):
            continue
        rows = []
        for tr in node.xpath("./thead/tr|./tbody/tr|./tr"):
            cells = [clean(" ".join(cell.itertext())) for cell in tr.xpath("./th|./td")]
            if any(cells):
                rows.append(cells)
        record = table_record(page, heading, rows) if rows else None
        if record:
            records.append(record)
    return records


def parse_college(source_slug):
    folder = SOURCE / source_slug
    card_path = folder / "card.json"
    if not card_path.exists():
        raise FileNotFoundError(f"No saved CollegeDekho college at {folder}")
    import json

    card = json.loads(card_path.read_text(encoding="utf-8"))
    rank = clean(card.get("nirf_rank"))
    tables = []
    for page in PAGES:
        tables.extend(parse_page(folder, page))
    facts = {
        "source_slug": source_slug,
        "nirf_rank": int(rank) if rank.isdigit() else None,
        "fee_range": usable_fee(card.get("fee_range")),
        "average_package": clean(card.get("average_package")) or None,
        "ownership": clean(card.get("ownership")) or None,
        "approval": clean(card.get("approval")) or None,
        "exams": usable_exams(card.get("exams")),
    }
    return facts, tables
