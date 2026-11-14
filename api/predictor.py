"""Engineering rank check against JoSAA 2026 and CSAB special rounds."""

import re
import sys
from functools import lru_cache
from pathlib import Path

PREDICTION = Path(__file__).resolve().parents[1] / "prediction"
if str(PREDICTION) not in sys.path:
    sys.path.insert(0, str(PREDICTION))

from institutes import HOME_STATES
from match import family_counts, predict, shortlist
from predict import CATEGORIES, load_csab, load_seats

PAGE_SIZE = 10
CHANCE_ORDER = {"safer": 0, "possible": 1, "unlikely": 2}
PHRASES = (
    ("indian institute of technology", "iit"),
    ("national institute of technology", "nit"),
    ("indian institute of information technology", "iiit"),
    ("indian institute of engineering science and technology", "iiest"),
    ("new delhi", "delhi"),
)
DROP = {"of", "the", "and", "for", "at", "in", "de", "dr"}
ALIASES = {
    "bombay": "mumbai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "banaras": "varanasi",
    "benares": "varanasi",
    "trichy": "tiruchirappalli",
    "baroda": "vadodara",
    "trivandrum": "thiruvananthapuram",
}
GENERIC_EXTRA = {"university", "technology", "campus", "deemed"}
PART = re.compile(
    r"department|faculty|school of|centre|center|management studies|\bdms\b|\bidc\b",
    re.I,
)
QUOTA_LABEL = {
    "AI": "All India",
    "HS": "Home state",
    "OS": "Other state",
    "GO": "Goa",
    "JK": "Jammu and Kashmir",
    "LA": "Ladakh",
}
CHANCE_LABEL = {"safer": "Safer", "possible": "Possible", "unlikely": "Unlikely"}


def form_options():
    return {
        "exams": ["JEE Main", "JEE Advanced"],
        "categories": [
            {"value": "OPEN", "label": "General"},
            {"value": "EWS", "label": "EWS"},
            {"value": "OBC-NCL", "label": "OBC-NCL"},
            {"value": "SC", "label": "SC"},
            {"value": "ST", "label": "ST"},
        ],
        "genders": [
            {"value": "male", "label": "Male"},
            {"value": "female", "label": "Female"},
        ],
        "states": list(HOME_STATES),
    }


def whole_number(value):
    text = str(value or "").replace(",", "").strip()
    return int(text) if text.isdigit() else None


def student_from_form(exam, rank, category, gender, home_state, crl):
    chosen_exam = exam.strip()
    if chosen_exam not in ("JEE Main", "JEE Advanced"):
        raise ValueError("Choose JEE Main or JEE Advanced.")
    chosen_category = CATEGORIES.get(category.strip().upper())
    if chosen_category is None:
        raise ValueError("Choose a category.")
    if gender not in ("male", "female"):
        raise ValueError("Choose male or female.")
    if home_state not in HOME_STATES:
        raise ValueError("Choose a home state.")
    rank_number = whole_number(rank)
    if rank_number is None or rank_number < 1:
        raise ValueError("Enter a rank of 1 or more.")
    common_rank = whole_number(crl) if str(crl or "").strip() else None
    if chosen_exam == "JEE Main" and chosen_category != "OPEN":
        if common_rank is None or common_rank < 1:
            raise ValueError(
                "Enter the common rank as well. CSAB publishes EWS, OBC-NCL, SC, and ST closing ranks on the common rank list."
            )
    else:
        common_rank = rank_number
    return {
        "exam": chosen_exam,
        "rank": rank_number,
        "crl": common_rank,
        "category": chosen_category,
        "gender": gender,
        "home_state": home_state,
        "course": "",
    }


def name_key(value):
    text = (value or "").lower().replace("&", " and ")
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    for old, new in PHRASES:
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = []
    for token in text.split():
        if len(token) <= 1 or token in DROP:
            continue
        tokens.append(ALIASES.get(token, token))
    return frozenset(tokens)


def college_index(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.slug, c.name, f.nirf_rank, f.fee_range
            FROM colleges c
            LEFT JOIN engineering_facts f ON f.college_slug = c.slug
            WHERE c.is_active IS TRUE
            """
        )
        rows = cursor.fetchall()
    grouped = {}
    postings = {}
    for row in rows:
        key = name_key(row["name"])
        grouped.setdefault(key, []).append(row)
        for token in key:
            postings.setdefault(token, set()).add(key)
    return grouped, postings


def candidate_keys(postings, key):
    lists = []
    for token in key:
        found = postings.get(token)
        if not found:
            return []
        lists.append(found)
    lists.sort(key=len)
    common = set(lists[0])
    for item in lists[1:]:
        common &= item
        if not common:
            return []
    return common


def choose_college(matches):
    institutes = [row for row in matches if not PART.search(row["name"] or "")]
    pool = institutes or []
    if len(pool) == 1:
        return pool[0]
    if len(pool) > 1:
        ranked = sorted(
            pool,
            key=lambda row: (
                row["nirf_rank"] is None,
                "admission" in (row["name"] or "").lower(),
                len(row["name"] or ""),
            ),
        )
        if ranked[0]["name"].casefold() != ranked[1]["name"].casefold():
            return None
        return ranked[0]
    return None


def extra_is_harmless(extra):
    return all(token in GENERIC_EXTRA or (token.isalpha() and 2 <= len(token) <= 8) for token in extra)


def linked_college(index, postings, institute):
    key = name_key(institute)
    chosen = choose_college(index.get(key) or [])
    if chosen is None and key:
        hits = []
        for other in candidate_keys(postings, key):
            extra = other - key
            if not extra or not extra_is_harmless(extra):
                continue
            match = choose_college(index.get(other) or [])
            if match is not None:
                hits.append(match)
        if len(hits) == 1:
            chosen = hits[0]
    if chosen is None:
        return {"slug": None, "nirf": None, "fee": None}
    return {
        "slug": chosen["slug"],
        "nirf": chosen["nirf_rank"],
        "fee": chosen["fee_range"],
    }


def present_rows(rows, index, postings):
    shown = []
    for row in rows:
        college = linked_college(index, postings, row["college"])
        shown.append(
            {
                "college": row["college"],
                "slug": college["slug"],
                "state": row["college_state"],
                "branch": row["branch"],
                "family": row["family"],
                "quota": QUOTA_LABEL.get(row["quota"], row["quota"]),
                "gender": "Female-only" if str(row["gender"]).startswith("Female-only") else "",
                "openingRank": row.get("opening_rank"),
                "closingRank": row["closing_rank"],
                "round": row.get("round") or "",
                "roundName": "CSAB round" if row.get("source") == "CSAB" else "JoSAA",
                "chance": CHANCE_LABEL.get(row["chance"], row["chance"]),
                "nirf": college["nirf"],
                "fee": college["fee"],
            }
        )
    return shown


def college_groups(rows):
    """Every branch of a college stays together, best chance first."""
    grouped = {}
    order = []
    for row in rows:
        key = row["college"]
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    colleges = []
    for key in order:
        seats = sorted(
            grouped[key],
            key=lambda seat: (CHANCE_ORDER.get(seat["chance"], 9), seat["closing_rank"], seat["branch"]),
        )
        colleges.append(seats)
    colleges.sort(
        key=lambda seats: (
            CHANCE_ORDER.get(seats[0]["chance"], 9),
            seats[0]["closing_rank"],
            seats[0]["college"],
        )
    )
    return colleges


def page_of(rows, page, branch, index, postings):
    families = family_counts(rows)
    chosen = [row for row in rows if row["family"] == branch] if branch else rows
    colleges = college_groups(chosen)
    page_count = max(1, (len(colleges) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, page_count)
    start = (page - 1) * PAGE_SIZE
    visible = [seat for seats in colleges[start : start + PAGE_SIZE] for seat in seats]
    return {
        "total": len(colleges),
        "pageSize": PAGE_SIZE,
        "families": families,
        "rows": present_rows(visible, index, postings),
    }


def ordered(student, seats):
    rows, counts = shortlist(predict(student, seats), student["rank"])
    if rows and rows[0].get("probability") != "low":
        rows.sort(key=lambda row: (row["closing_rank"], row["college"], row["branch"]))
    inside = counts.get("very-high", 0) + counts.get("high", 0) + counts.get("medium", 0)
    return rows, inside


@lru_cache(maxsize=1)
def josaa_by_exam():
    grouped = {"JEE Main": [], "JEE Advanced": []}
    for seat in load_seats():
        if seat["exam"] in grouped:
            grouped[seat["exam"]].append(seat)
    return grouped


@lru_cache(maxsize=1)
def csab_seats():
    return tuple(load_csab())


def listed_rows(rows, inside):
    """Keep real matches. Stretch seats are used only when no round has a match."""
    return rows if inside else []


def prediction_payload(connection, student, branch, page):
    josaa_rows, josaa_inside = ordered(student, josaa_by_exam()[student["exam"]])
    csab_rows, csab_inside = [], 0
    if student["exam"] == "JEE Main":
        csab_rows, csab_inside = ordered(dict(student, rank=student["crl"]), csab_seats())
    combined = listed_rows(josaa_rows, josaa_inside) + listed_rows(csab_rows, csab_inside)
    if not combined:
        combined = josaa_rows + csab_rows
    index, postings = college_index(connection)
    if student["exam"] == "JEE Advanced":
        detail = "IIT seats from JoSAA 2026 Round 5. CSAB does not allot IIT seats."
    else:
        detail = "One list. JoSAA is the main round. A CSAB tag means the seat was filled later, in the special round."
    sections = [
        {
            "id": "seats",
            "title": "Colleges for this rank",
            "detail": detail,
            "inside": josaa_inside + csab_inside,
            "josaaInside": josaa_inside,
            "csabInside": csab_inside if student["exam"] == "JEE Main" else None,
            **page_of(combined, page, branch, index, postings),
        }
    ]
    category_label = next(
        item["label"] for item in form_options()["categories"] if item["value"] == student["category"]
    )
    return {
        "exam": student["exam"],
        "rank": student["rank"],
        "crl": student["crl"] if student["exam"] == "JEE Main" and student["category"] != "OPEN" else None,
        "category": category_label,
        "gender": "Female" if student["gender"] == "female" else "Male",
        "homeState": student["home_state"],
        "branch": branch,
        "note": "These chances follow the 2026 closing ranks. A later counselling year can move, so this is not a guaranteed seat.",
        "sections": sections,
    }

