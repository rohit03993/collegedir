import os
import re

import typesense
from dotenv import load_dotenv
from typesense.exceptions import ObjectNotFound, TypesenseClientError

from api.db import ROOT
from api.format import rating_value

COLLECTION = "colleges"

SCHEMA = {
    "name": COLLECTION,
    "fields": [
        {"name": "slug", "type": "string"},
        {"name": "name", "type": "string", "sort": True},
        {"name": "city", "type": "string", "facet": True, "optional": True},
        {"name": "state", "type": "string", "facet": True, "optional": True},
        {"name": "type", "type": "string", "optional": True, "index": False},
        {"name": "category", "type": "string", "facet": True, "optional": True},
        {"name": "course_groups", "type": "string[]", "facet": True, "optional": True},
        {"name": "branches", "type": "string[]", "facet": True, "optional": True},
        {"name": "course_group", "type": "string", "optional": True, "index": False},
        {"name": "fee_label", "type": "string", "optional": True, "index": False},
        {"name": "image", "type": "string", "optional": True, "index": False},
        {"name": "rating", "type": "float", "optional": True},
        {"name": "priority", "type": "int32"},
        {"name": "engineering_rank", "type": "int32", "optional": True},
        {"name": "established", "type": "int32", "optional": True},
        {"name": "aliases", "type": "string", "optional": True},
    ],
    "default_sorting_field": "priority",
}

FIELDS = {
    "state": "state",
    "city": "city",
    "course": "course_groups",
    "branch": "branches",
    "stream": "category",
}

# Old and current spellings of the same place. Both forms are already in the catalogue.
PLACE_PAIRS = (
    ("newdelhi", "delhi"),
    ("delhincr", "delhi"),
    ("bombay", "mumbai"),
    ("madras", "chennai"),
    ("calcutta", "kolkata"),
    ("bangalore", "bengaluru"),
    ("gurgaon", "gurugram"),
    ("trivandrum", "thiruvananthapuram"),
    ("cochin", "kochi"),
    ("pondicherry", "puducherry"),
    ("banaras", "varanasi"),
    ("benares", "varanasi"),
    ("mysore", "mysuru"),
    ("trichy", "tiruchirappalli"),
    ("baroda", "vadodara"),
    ("calicut", "kozhikode"),
    ("belgaum", "belagavi"),
    ("allahabad", "prayagraj"),
    ("gauhati", "guwahati"),
    ("poona", "pune"),
    ("mangalore", "mangaluru"),
    ("hubli", "hubballi"),
    ("shimoga", "shivamogga"),
    ("bellary", "ballari"),
    ("tumkur", "tumakuru"),
    ("gulbarga", "kalaburagi"),
    ("bijapur", "vijayapura"),
    ("hospet", "hosapete"),
    ("nasik", "nashik"),
    ("simla", "shimla"),
    ("tuticorin", "thoothukudi"),
    ("palghat", "palakkad"),
    ("trichur", "thrissur"),
    ("alleppey", "alappuzha"),
    ("quilon", "kollam"),
    ("tanjore", "thanjavur"),
    ("panjim", "panaji"),
    ("cannanore", "kannur"),
    ("cawnpore", "kanpur"),
    ("vizag", "visakhapatnam"),
    ("waltair", "visakhapatnam"),
    ("jubbulpore", "jabalpur"),
)
SYNONYM_SET = "college-places"
# The public name says IITM, and people search for IIT.
SLUG_ALIASES = {
    "indian-institute-of-technology-madras-iitm-chennai": "indian institute of technology iit",
}
PART = re.compile(
    r"department|faculty|school of|centre|center|management studies|\bdms\b|\bidc\b",
    re.I,
)
_synonyms_ready = False
_aliases_ready = False


class SearchUnavailable(RuntimeError):
    pass


def client():
    load_dotenv(ROOT / ".env")
    key = os.environ.get("TYPESENSE_API_KEY", "").strip()
    if not key:
        raise SearchUnavailable("TYPESENSE_API_KEY is not set.")
    try:
        port = int(os.environ.get("TYPESENSE_PORT", "8108"))
    except ValueError as exc:
        raise SearchUnavailable("TYPESENSE_PORT must be a number.") from exc
    return typesense.Client(
        {
            "nodes": [
                {
                    "host": os.environ.get("TYPESENSE_HOST", "127.0.0.1"),
                    "port": port,
                    "protocol": os.environ.get("TYPESENSE_PROTOCOL", "http"),
                }
            ],
            "api_key": key,
            "connection_timeout_seconds": 3,
        }
    )


def recreate_collection(typesense):
    try:
        typesense.collections[COLLECTION].delete()
    except ObjectNotFound:
        pass
    typesense.collections.create(SCHEMA)


def safe_value(value):
    return " ".join(value.replace("`", " ").replace("&&", " ").replace("||", " ").split())


def limit_values(values):
    chosen = []
    for value in values:
        text = value.strip()
        if not text or len(text) > 120 or text in chosen:
            continue
        chosen.append(text)
        if len(chosen) >= 20:
            break
    return chosen


def clause(field, values):
    parts = []
    for value in values:
        text = safe_value(value)
        if text:
            parts.append(f"{field}:=`{text}`")
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return "(" + " || ".join(parts) + ")"


def filter_by(selected, omit=None):
    parts = []
    for key, field in FIELDS.items():
        if key == omit:
            continue
        piece = clause(field, selected.get(key) or [])
        if piece:
            parts.append(piece)
    return " && ".join(parts)


def sort_clause(query, selected):
    if query:
        return "_text_match:desc,engineering_rank(missing_values: last):asc,priority:desc"
    streams = {value.casefold() for value in selected.get("stream") or []}
    if "engineering" in streams:
        return "engineering_rank(missing_values: last):asc,priority:desc,name:asc"
    return "priority:desc,name:asc"


def ensure_place_synonyms(typesense):
    """Teach the index that Bombay and Mumbai are the same place.

    Typesense 30 keeps these in a synonym set. A search then has to match
    every word, so an unknown place is not silently ignored.
    """
    global _synonyms_ready
    if _synonyms_ready:
        return
    items = []
    seen = set()
    for left, right in PLACE_PAIRS:
        pair = tuple(sorted((left, right)))
        if pair in seen:
            continue
        seen.add(pair)
        items.append({"id": f"place-{pair[0]}-{pair[1]}", "synonyms": [pair[0], pair[1]]})
    # Madras is stored as IITM, so the word IIT has to find that record too.
    typesense.api_call.put(f"/synonym_sets/{SYNONYM_SET}", dict, {"items": items})
    _synonyms_ready = True


def ensure_aliases(typesense):
    """Add the alias field once, then fill the few colleges that need it."""
    global _aliases_ready
    if _aliases_ready:
        return
    try:
        typesense.collections[COLLECTION].update(
            {"fields": [{"name": "aliases", "type": "string", "optional": True}]}
        )
    except TypesenseClientError as exc:
        if "already" not in str(exc).lower() and "exists" not in str(exc).lower():
            raise
    for slug, alias in SLUG_ALIASES.items():
        typesense.collections[COLLECTION].documents[slug].update({"aliases": alias})
    _aliases_ready = True


def prefer_institutes(query, colleges):
    """Keep a department below the institute when the search did not ask for one."""
    if not query or PART.search(query):
        return colleges
    primary = [college for college in colleges if not PART.search(college["name"] or "")]
    if not primary:
        return colleges
    extra = [college for college in colleges if PART.search(college["name"] or "")]
    return primary + extra


def base_params(query, selected, omit=None):
    params = {
        "collection": COLLECTION,
        "q": query or "*",
        "query_by": "name,aliases,city,state,course_groups,branches" if _aliases_ready else "name,city,state,course_groups,branches",
        "query_by_weights": "8,8,3,3,4,4" if _aliases_ready else "8,3,3,4,4",
        "sort_by": sort_clause(query, selected),
        "drop_tokens_threshold": 0,
        "synonym_sets": SYNONYM_SET,
    }
    filtered = filter_by(selected, omit)
    if filtered:
        params["filter_by"] = filtered
    return params


def card_from_doc(document):
    image = document.get("image")
    if not image or not str(image).startswith("/media/"):
        image = None
    return {
        "slug": document.get("slug") or document.get("id"),
        "name": document.get("name"),
        "city": document.get("city"),
        "state": document.get("state"),
        "ownership": document.get("type"),
        "courseGroup": document.get("course_group"),
        "fee": document.get("fee_label"),
        "rating": rating_value(document.get("rating")),
        "image": image,
    }


def facet_values(result):
    values = []
    for facet in result.get("facet_counts") or []:
        for count in facet.get("counts") or []:
            if count.get("value"):
                values.append({"value": count["value"], "count": count["count"]})
    return values


def with_selected(values, selected):
    found = {item["value"] for item in values}
    for value in selected:
        if value not in found:
            values.append({"value": value, "count": 0})
    return values


def search_colleges(q, state, city, course, branch, stream, page, per_page):
    selected = {
        "state": limit_values(state),
        "city": limit_values(city),
        "course": limit_values(course),
        "branch": limit_values(branch),
        "stream": limit_values(stream),
    }
    query = (q or "").strip()[:80]
    typesense = client()
    try:
        ensure_place_synonyms(typesense)
        ensure_aliases(typesense)
    except (TypesenseClientError, OSError):
        pass
    searches = [base_params(query, selected)]
    searches[0]["page"] = page
    searches[0]["per_page"] = per_page
    for key in FIELDS:
        params = base_params(query, selected, omit=key)
        params["page"] = 1
        params["per_page"] = 0
        params["facet_by"] = FIELDS[key]
        params["max_facet_values"] = 80 if key in {"state", "stream", "course"} else 40
        searches.append(params)
    try:
        response = typesense.multi_search.perform({"searches": searches}, {})
    except (TypesenseClientError, OSError) as exc:
        raise SearchUnavailable(
            "Search index is not available. Start Typesense and run python db/index_search.py."
        ) from exc
    results = response.get("results") or []
    if not results or results[0].get("error"):
        raise SearchUnavailable(
            "Search index is not available. Start Typesense and run python db/index_search.py."
        )
    hits = results[0]
    facets = {}
    for key, result in zip(FIELDS, results[1:]):
        values = facet_values(result)
        values = with_selected(values, selected[key])
        facets[key] = values
    return {
        "total": hits.get("found", 0),
        "query": query,
        "colleges": prefer_institutes(
            query,
            [card_from_doc(hit["document"]) for hit in hits.get("hits") or []],
        ),
        "facets": facets,
    }
