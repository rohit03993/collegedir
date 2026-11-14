"""Save CSAB Special 2026 opening and closing ranks.

The official form is institute by institute. Choosing All for institute
type, institute, and program returns one full round. This script does
that for special round 1 and special round 2.

Every rank on this page is an All India common rank (CRL), including
SC, ST, EWS, and OBC-NCL rows. That is different from JoSAA, where
those categories use their own rank lists.

From the project folder:

    python prediction\\export_csab.py
"""

from __future__ import annotations

import csv
import html
import http.cookiejar
import re
import urllib.parse
import urllib.request
from pathlib import Path

PAGE = "https://admissions.nic.in/csabspl/Applicant/seatallotmentresult/currentorcr.aspx"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "csab-2026-special-orcr.csv"

ROUND = "ctl00$ContentPlaceHolder1$ddlroundno"
INST_TYPE = "ctl00$ContentPlaceHolder1$ddlInstype"
INSTITUTE = "ctl00$ContentPlaceHolder1$ddlInstitute"
PROGRAM = "ctl00$ContentPlaceHolder1$ddlBranch"
SUBMIT = "ctl00$ContentPlaceHolder1$btnSubmit"

COLUMNS = [
    "Year",
    "Round",
    "Exam",
    "Institute",
    "Academic Program Name",
    "Quota",
    "Seat Type",
    "Gender",
    "Opening Rank",
    "Closing Rank",
    "Rank List",
]


def opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def fetch(client, data: dict | None = None) -> str:
    encoded = None if data is None else urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        PAGE,
        data=encoded,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": PAGE,
            "Accept": "text/html",
        },
    )
    with client.open(request, timeout=180) as response:
        return response.read().decode("utf-8", errors="replace")


def tag_attrs(tag: str) -> dict:
    return {name: html.unescape(value) for name, value in re.findall(r'([^\s=]+)="([^"]*)"', tag)}


def hidden_fields(page: str) -> dict:
    fields = {}
    for tag in re.findall(r"<input\b[^>]*>", page, flags=re.I):
        attrs = tag_attrs(tag)
        name = attrs.get("name")
        if name and attrs.get("type", "").lower() == "hidden":
            fields[name] = attrs.get("value", "")
    return fields


def selects(page: str) -> dict:
    found = {}
    for tag, body in re.findall(r"<select\b([^>]*)>(.*?)</select>", page, flags=re.I | re.S):
        attrs = tag_attrs(tag)
        name = attrs.get("name")
        if not name:
            continue
        options = []
        selected = None
        for option_tag, text in re.findall(r"<option\b([^>]*)>(.*?)</option>", body, flags=re.I | re.S):
            option_attrs = tag_attrs(option_tag)
            value = option_attrs.get("value", re.sub(r"<[^>]+>", "", text).strip())
            options.append(value)
            if re.search(r"\bselected\b", option_tag, flags=re.I):
                selected = value
        if selected is None and options:
            selected = options[0]
        found[name] = {"options": options, "selected": selected}
    return found


def post_form(client, page: str, event_target: str, updates: dict) -> str:
    fields = hidden_fields(page)
    fields["__EVENTTARGET"] = event_target
    fields["__EVENTARGUMENT"] = ""
    for name, spec in selects(page).items():
        if spec["selected"] is not None:
            fields[name] = spec["selected"]
    fields.update(updates)
    return fetch(client, fields)


def choose(client, page: str, control: str, value: str) -> str:
    spec = selects(page).get(control)
    options = spec["options"] if spec else []
    if value not in options:
        shown = ", ".join(options[:8]) or "none"
        raise RuntimeError(f"{control} has no option {value!r}. First options: {shown}")
    print(f"  {control.rsplit('$', 1)[-1]} = {value}")
    return post_form(client, page, control, {control: value})


def table_rows(page: str) -> list[list[str]]:
    match = re.search(
        r'id="ctl00_ContentPlaceHolder1_GridView1".*?</table>',
        page,
        flags=re.I | re.S,
    )
    if not match:
        return []
    rows = []
    for raw in re.findall(r"<tr\b[^>]*>(.*?)</tr>", match.group(0), flags=re.I | re.S):
        cells = [
            re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()
            for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", raw, flags=re.I | re.S)
        ]
        if len(cells) == 7 and cells[5].isdigit() and cells[6].isdigit():
            rows.append(cells)
    return rows


def one_round(client, round_no: str) -> list[list[str]]:
    page = fetch(client)
    page = choose(client, page, ROUND, round_no)
    page = choose(client, page, INST_TYPE, "ALL")
    page = choose(client, page, INSTITUTE, "ALL")
    print("  program = ALL")
    page = post_form(client, page, "", {PROGRAM: "ALL", SUBMIT: "Submit"})
    rows = table_rows(page)
    if rows:
        return rows
    debug = HERE / f"csab-round-{round_no}-debug.html"
    debug.write_text(page, encoding="utf-8")
    if "Invalid postback" in page:
        reason = "the form rejected the request"
    elif "ddlroundno" not in page:
        reason = "the rank page did not load"
    else:
        reason = "the result table was missing"
    print(f"  {reason}. Saved {debug.name}")
    return []


def main() -> None:
    saved = []
    for round_no in ("1", "2"):
        rows = one_round(opener(), round_no)
        print(f"special round {round_no}: {len(rows)} seats")
        for institute, program, quota, seat_type, gender, opening, closing in rows:
            saved.append(
                [
                    "2026",
                    round_no,
                    "JEE Main",
                    institute,
                    program,
                    quota,
                    seat_type,
                    gender,
                    opening,
                    closing,
                    "CRL",
                ]
            )
    if not saved:
        raise SystemExit("No CSAB rows were returned. The official form may have changed.")
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(saved)
    print(f"saved {len(saved)} seats to {OUTPUT}")


if __name__ == "__main__":
    main()
