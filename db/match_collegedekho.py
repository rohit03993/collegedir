"""Match saved CollegeDekho colleges to Admission Setu slugs.

A department or school inside a campus loses to the institute itself.
Two CollegeDekho records are not given the same Admission Setu college.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

LISTING = Path(r"F:\Rohit Development\admission setu\college-dekho\data\listing.json")
PART = re.compile(
    r"department|faculty|school of|centre|center|management studies|\bdms\b|\bidc\b",
    re.I,
)
CITY_ALIASES = {
    "newdelhi": "delhi",
    "delhincr": "delhi",
    "bombay": "mumbai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "bangalore": "bengaluru",
    "gurgaon": "gurugram",
    "trivandrum": "thiruvananthapuram",
    "cochin": "kochi",
    "pondicherry": "puducherry",
    "banaras": "varanasi",
    "mysore": "mysuru",
    "trichy": "tiruchirappalli",
    "baroda": "vadodara",
    "calicut": "kozhikode",
    "belgaum": "belagavi",
    "allahabad": "prayagraj",
    "gauhati": "guwahati",
    "poona": "pune",
    "mangalore": "mangaluru",
    "hubli": "hubballi",
    "shimoga": "shivamogga",
    "bellary": "ballari",
    "tumkur": "tumakuru",
    "gulbarga": "kalaburagi",
    "bijapur": "vijayapura",
    "hospet": "hosapete",
    "nasik": "nashik",
    "simla": "shimla",
    "tuticorin": "thoothukudi",
    "palghat": "palakkad",
    "trichur": "thrissur",
    "alleppey": "alappuzha",
    "quilon": "kollam",
    "tanjore": "thanjavur",
    "panjim": "panaji",
    "cannanore": "kannur",
    "cawnpore": "kanpur",
    "vizag": "visakhapatnam",
    "waltair": "visakhapatnam",
    "benares": "varanasi",
    "jubbulpore": "jabalpur",
}


REPLACEMENTS = (
    ("indian institute of technology", "iit"),
    ("national institute of technology", "nit"),
    ("indian institute of information technology", "iiit"),
    ("vellore institute of technology", "vit"),
    ("delhi technological university", "dtu"),
    ("lovely professional university", "lpu"),
    ("birla institute of technology and science", "bits"),
    ("new delhi", "delhi"),
    ("gandhi nagar", "gandhinagar"),
    ("bombay", "mumbai"),
    ("madras", "chennai"),
)
KEEP_OUT = {"admission"}


FILLER = {"of", "the", "and", "for", "at", "in", "to", "de", "by"}
GENERIC = {
    "university", "college", "institute", "engineering", "technology", "science",
    "sciences", "management", "education", "campus", "school", "research",
    "studies", "applied", "national", "indian",
}
CONFLICT = {
    "pharmacy", "nursing", "medical", "dental", "law", "hotel", "hospital",
    "ayurveda", "homoeopathic", "polytechnic",
}
CAMPUS_PAIRS = (
    frozenset({"mohali", "chandigarh"}),
    frozenset({"bhilai", "durg"}),
    frozenset({"phagwara", "jalandhar"}),
    frozenset({"kundli", "sonepat"}),
    frozenset({"nirjuli", "itanagar"}),
    frozenset({"anand", "vallabhvidyanagar"}),
    frozenset({"navimumbai", "mumbai"}),
)


def collapse_initials(text):
    text = re.sub(
        r"\b(?:[a-z]\.){2,}[a-z]?\b",
        lambda match: match.group(0).replace(".", ""),
        text,
    )
    return re.sub(
        r"\b(?:[a-z] ){2,}[a-z]\b",
        lambda match: match.group(0).replace(" ", ""),
        text,
    )


def normalize(name):
    text = (name or "").lower().replace("&", " and ")
    text = collapse_initials(text)
    text = re.sub(r"[\[\]]", " ", text)
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [
        CITY_ALIASES.get(token, token)
        for token in text.split()
        if len(token) > 1 and token not in FILLER
    ]


def tokens(name):
    stop = {
        "of", "the", "and", "for", "at", "in", "college", "institute", "university",
        "campus", "technology", "engineering", "deemed", "to", "be", "research", "education",
    }
    return [token for token in normalize(name) if token not in stop]


def bracket_codes(name):
    codes = set()
    for code in re.findall(r"\[([^\]]+)\]", name or ""):
        raw = code.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9&.-]{1,12}", raw):
            continue
        parts = normalize(raw)
        if len(parts) == 1 and 2 <= len(parts[0]) <= 10:
            codes.add(parts[0])
    return codes


def paren_codes(name):
    codes = set()
    for code in re.findall(r"\(([A-Za-z][A-Za-z0-9.& ]{0,12})\)", name or ""):
        parts = normalize(code)
        if parts and all(len(part) <= 6 for part in parts):
            codes.update(parts)
    return codes


def identity(name, city):
    skip = set(normalize(city)) | bracket_codes(name) | KEEP_OUT
    return {token for token in normalize(name) if token not in skip}


def same_college(source_name, source_city, dest_name, dest_city):
    """True when the short name is the same college, including old city spellings.

    A university is not attached to a different college that only shares a city
    or a short word. A bracket code such as VTU may match the long name.
    """
    if not cities_agree(city_key(source_city), city_key(dest_city)):
        return False
    source_ids = identity(source_name, source_city)
    dest_ids = identity(dest_name, dest_city)
    if source_ids and source_ids == dest_ids:
        return True
    extra = source_ids - dest_ids
    if source_ids and dest_ids and not (dest_ids - source_ids) and extra <= paren_codes(source_name):
        return True
    short = set(tokens(source_name)) - set(normalize(source_city))
    codes = bracket_codes(dest_name)
    return bool(short) and short <= codes and all(2 <= len(token) <= 6 for token in short)


def city_key(value):
    text = re.sub(r"[^a-z]", "", (value or "").lower())
    return CITY_ALIASES.get(text, text)


def cities_agree(left, right):
    if not left or not right:
        return True
    return left == right


def places_agree(left, right):
    if cities_agree(left, right):
        return True
    return bool(left and right) and frozenset({left, right}) in CAMPUS_PAIRS


def conflict_kinds(name):
    text = set(normalize(name))
    return {kind for kind in CONFLICT if kind in text}


def core_name(name, city):
    codes = bracket_codes(name)
    words = [token for token in normalize(name) if token not in codes and token not in KEEP_OUT]
    city_words = set(normalize(city))
    kept = [token for token in words if token not in city_words]
    if any(token not in GENERIC for token in kept):
        return set(kept)
    return set(words)


def blocked_target(source_name, college):
    if PART.search(college["name"]) and not PART.search(source_name or ""):
        return True
    if conflict_kinds(college["name"]) - conflict_kinds(source_name):
        return True
    source_words = set(normalize(source_name))
    dest_words = set(normalize(college["name"]))
    if ("management" in source_words) != ("management" in dest_words):
        if ("engineering" in source_words) != ("engineering" in dest_words):
            if "management" in source_words or "management" in dest_words:
                return True
    city_words = set(normalize(college.get("raw_city") or college.get("city")))
    codes = college.get("codes") or bracket_codes(college["name"])
    own = [
        token for token in normalize(source_name)
        if token not in GENERIC and token not in city_words and token not in codes
    ]
    dest_own = dest_words - GENERIC - codes - city_words
    if len(own) >= 3 and sum(token in dest_words or token in codes for token in own) * 2 < len(own):
        return True
    if own and dest_own and not (set(own) & dest_own):
        return True
    if "campus" in dest_words and "campus" not in source_words and len(own) <= 1:
        return True
    return False


def _best(rows, source_words):
    chosen = []
    seen = set()
    for college in rows:
        if college["slug"] in seen:
            continue
        seen.add(college["slug"])
        chosen.append(college)
    if len(chosen) == 1:
        return chosen[0]
    covering = []
    for college in chosen:
        have = set(normalize(college["name"])) | college["codes"]
        if source_words and source_words <= have:
            covering.append(college)
    if len(covering) == 1:
        return covering[0]
    if len(covering) > 1:
        covering.sort(key=lambda college: len(set(normalize(college["name"]))))
        smallest = set(normalize(covering[0]["name"]))
        if all(smallest <= set(normalize(college["name"])) for college in covering[1:]):
            return covering[0]
    return None


def _prefer_real(college, by_city):
    if "admission" not in college["name"].lower():
        return college
    siblings = []
    label = college["name"].lower()
    for other in by_city.get(college["city"], []):
        if other["slug"] == college["slug"] or "admission" in other["name"].lower():
            continue
        if label.startswith(other["name"].lower()):
            siblings.append(other)
    if len(siblings) == 1:
        return siblings[0]
    return college


def _near_code(code, token):
    gap = len(code) - len(token)
    if gap <= 0 or gap > 3 or len(token) < 4:
        return False
    if code.startswith(token):
        return gap <= 2
    return code.endswith(token)


def match_existing(colleges, cards):
    """Attach a short or full CollegeDekho name to one catalogue college.

    A bracket code that exists once can match across an old city spelling.
    A shared code such as NIT still needs the city to leave one college.
    """
    prepared = []
    by_city = defaultdict(list)
    by_code = defaultdict(list)
    by_core = defaultdict(list)
    for college in colleges:
        item = {
            "slug": college["slug"],
            "name": college["name"],
            "city": city_key(college.get("city")),
            "raw_city": college.get("city") or "",
            "raw_state": college.get("state") or "",
            "codes": bracket_codes(college["name"]),
        }
        item["core"] = core_name(college["name"], college.get("city"))
        prepared.append(item)
        by_city[item["city"]].append(item)
        by_core[frozenset(item["core"])].append(item)
        for code in item["codes"]:
            if 2 <= len(code) <= 10:
                by_code[code].append(item)

    def local_rows(city):
        rows = list(by_city.get(city, []))
        for pair in CAMPUS_PAIRS:
            if city in pair:
                other = next(iter(pair - {city}))
                rows.extend(by_city.get(other, []))
        return rows

    def pick(card):
        name = card.get("college_name") or ""
        city = city_key(card.get("city"))
        source_words = set(normalize(name))
        shorts = [token for token in tokens(name) if token != city and 2 <= len(token) <= 10]
        exact_local = []
        prefix_local = []
        short_name = [token for token in normalize(name) if token != city]
        allow_prefix = len(short_name) == 1
        for college in local_rows(city):
            if blocked_target(name, college):
                continue
            for code in college["codes"]:
                for token in shorts:
                    if code == token:
                        exact_local.append(college)
                    elif allow_prefix and len(token) >= 4 and _near_code(code, token):
                        prefix_local.append(college)
        only = _best(exact_local, source_words)
        if only:
            return only
        named = [
            college for college in by_core.get(frozenset(core_name(name, card.get("city"))), [])
            if places_agree(city, college["city"]) and not blocked_target(name, college)
        ]
        plain = [college for college in named if "admission" not in college["name"].lower()]
        only = _best(plain or named, source_words)
        if only:
            return only
        only = _best(prefix_local, source_words)
        if only:
            return only
        place_hits = []
        for token in shorts:
            places = [part for part in shorts if part != token and len(part) >= 3]
            if not places:
                continue
            for college in by_code.get(token, []):
                if blocked_target(name, college):
                    continue
                where = set(normalize(college.get("raw_city")))
                where.update(normalize(college.get("raw_state")))
                if any(place in where for place in places):
                    place_hits.append(college)
        only = _best(place_hits, source_words)
        if only:
            return only
        if len(short_name) == 1 and 2 <= len(short_name[0]) <= 10:
            owners = [
                college for college in by_code.get(short_name[0], [])
                if places_agree(city, college["city"]) and not blocked_target(name, college)
            ]
            return _best(owners, source_words)
        return None

    matched = []
    skipped = []
    used = set()
    for card in cards:
        winner = pick(card)
        if winner is not None:
            winner = _prefer_real(winner, by_city)
        if winner is None or winner["slug"] in used:
            skipped.append(card.get("college_name") or card.get("slug"))
            continue
        used.add(winner["slug"])
        matched.append((card["slug"], winner["slug"]))
    return matched, skipped


def covered_tokens(name, city=""):
    text = f"{name or ''} {city or ''}".lower().replace("&", " and ")
    text = collapse_initials(text)
    text = re.sub(r"[\[\]]", " ", text)
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    raw = [CITY_ALIASES.get(token, token) for token in text.split() if token and token not in FILLER]
    glued = []
    pending = ""
    for word in raw:
        if len(word) == 1:
            pending += word
            continue
        if pending:
            if len(pending) > 1:
                glued.append(pending)
            pending = ""
        glued.append(word)
    if len(pending) > 1:
        glued.append(pending)
    return {word for word in glued if len(word) > 1 and word not in FILLER}


def name_ratio(source_name, source_city, dest_name, dest_city):
    """Share of the CollegeDekho name found on one Admission Setu college.

    A longer different college does not pass, and two cities do not pass
    unless the searched name itself contains that place.
    """
    source = covered_tokens(source_name, source_city)
    if not source:
        return 0.0
    dest = covered_tokens(dest_name, dest_city) | bracket_codes(dest_name)
    score = len(source & dest) / len(source)
    if score < 0.70:
        return score
    extra = (covered_tokens(dest_name) - GENERIC) - covered_tokens(source_name, source_city)
    extra -= bracket_codes(dest_name)
    extra -= covered_tokens(dest_city)
    if extra:
        return 0.0
    source_words = covered_tokens(source_name)
    dest_words = covered_tokens(dest_name)
    for word in CONFLICT | {"marine", "management"}:
        if (word in source_words) != (word in dest_words):
            return 0.0
    if PART.search(dest_name or "") and not PART.search(source_name or ""):
        return 0.0
    if not places_agree(city_key(source_city), city_key(dest_city)):
        if not (covered_tokens(source_name) & covered_tokens(dest_city)):
            return 0.0
    return score


def match_by_search(cards, taken):
    """Use the same college search as the site.

    One search result is the college. The CollegeDekho details go on that
    record. A search with several results is left unmatched.
    """
    from api.search import COLLECTION, SYNONYM_SET, client, ensure_place_synonyms

    typesense = client()
    try:
        ensure_place_synonyms(typesense)
    except Exception:
        pass
    matched = []
    skipped = []
    used = set(taken)
    for card in cards:
        name = card.get("college_name") or ""
        city = card.get("city") or ""
        query = name if city.casefold() in name.casefold() else f"{name} {city}"
        query = " ".join(query.split())[:80]
        try:
            result = typesense.collections[COLLECTION].documents.search(
                {
                    "q": query or "*",
                    "query_by": "name,city,state",
                    "query_by_weights": "8,3,3",
                    "per_page": 1,
                    "page": 1,
                    "drop_tokens_threshold": 0,
                    "synonym_sets": SYNONYM_SET,
                }
            )
        except Exception:
            skipped.append(name or card.get("slug"))
            continue
        hits = result.get("hits") or []
        if int(result.get("found") or 0) != 1 or not hits:
            skipped.append(name or card.get("slug"))
            continue
        doc = hits[0].get("document") or {}
        slug = doc.get("slug") or doc.get("id")
        if not slug or slug in used:
            skipped.append(name or card.get("slug"))
            continue
        used.add(slug)
        matched.append((card["slug"], slug, 1.0))
    return matched, skipped


def load_listing():
    return json.loads(LISTING.read_text(encoding="utf-8"))


def score(college, source_tokens):
    extra = len(set(college["tokens"]) - set(source_tokens))
    penalty = 25 if PART.search(college["name"]) or PART.search(college["slug"].replace("-", " ")) else 0
    stream = 0 if college["category"] == "Engineering" else 6
    return extra + penalty + stream


def choose(candidates, source_tokens):
    ranked = sorted(candidates, key=lambda college: (score(college, source_tokens), len(college["name"])))
    if len(ranked) == 1:
        return ranked[0]
    best, second = score(ranked[0], source_tokens), score(ranked[1], source_tokens)
    if second - best >= 6:
        return ranked[0]
    return None


def match_cards(colleges, cards):
    prepared = []
    by_token = defaultdict(list)
    by_squash = defaultdict(list)
    for college in colleges:
        parts = tokens(college["name"])
        item = {
            "slug": college["slug"],
            "name": college["name"],
            "category": college.get("category") or "",
            "city": city_key(college.get("city")),
            "tokens": parts,
        }
        prepared.append(item)
        squash = "".join(parts)
        if len(squash) >= 6:
            by_squash[squash].append(item)
        for token in set(parts):
            if len(token) >= 3:
                by_token[token].append(item)

    matched = []
    skipped = []
    used = set()
    for card in cards:
        parts = tokens(card.get("college_name"))
        source_city = city_key(card.get("city"))
        pool = []
        squash = "".join(parts)
        if len(squash) >= 6 and squash in by_squash:
            pool = list(by_squash[squash])
        else:
            buckets = [by_token.get(token, []) for token in parts if len(token) >= 3]
            buckets = [bucket for bucket in buckets if bucket]
            if buckets:
                pool = min(buckets, key=len)
        seen = set()
        candidates = []
        source_set = set(parts)
        for college in pool:
            if college["slug"] in seen:
                continue
            seen.add(college["slug"])
            ours = set(college["tokens"])
            same = source_set and (source_set <= ours or "".join(college["tokens"]) == squash)
            if not same or not cities_agree(source_city, college["city"]):
                continue
            if len(source_set) == 1 and len(next(iter(source_set))) <= 4 and source_city != college["city"]:
                continue
            candidates.append(college)
        winner = choose(candidates, parts) if candidates else None
        if winner is None or winner["slug"] in used:
            skipped.append(card.get("college_name") or card.get("slug"))
            continue
        used.add(winner["slug"])
        matched.append((card["slug"], winner["slug"]))
    return matched, skipped
