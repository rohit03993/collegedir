"""Order for the Engineering college list.

A lower number is shown first. Only the institute itself is ranked.
Departments inside an IIT keep their own category and stay in the normal order.
"""

CAMPUSES = (
    ("mumbai", 1),
    ("new-delhi", 2),
    ("delhi", 2),
    ("madras", 3),
    ("kanpur", 4),
    ("kharagpur", 5),
    ("roorkee", 6),
    ("guwahati", 7),
    ("hyderabad", 8),
    ("bhu-varanasi", 9),
    ("varanasi", 9),
    ("indore", 10),
    ("dhanbad", 11),
    ("gandhi-nagar", 12),
    ("gandhinagar", 12),
    ("ropar", 13),
    ("mandi", 14),
    ("jodhpur", 15),
    ("patna", 16),
    ("bhubaneswar", 17),
    ("tirupati", 18),
    ("iittp", 18),
    ("palakkad", 19),
    ("iitpkd", 19),
    ("bhilai", 20),
    ("jammu", 21),
)

SHORT_SLUGS = {"iit-kharagpur", "iit-roorkee"}


def is_iit_institute(slug, name):
    slug = (slug or "").strip().lower()
    name = (name or "").strip().lower()
    if slug.startswith("indian-institute-of-technology-"):
        return True
    if slug in SHORT_SLUGS or name in {"iit kharagpur", "iit roorkee"}:
        return True
    return False


def listing_category(slug, name, category):
    if is_iit_institute(slug, name):
        return "Engineering"
    return category


def engineering_rank(slug, name):
    if not is_iit_institute(slug, name):
        return None
    blob = f"{slug or ''} {name or ''}".lower()
    for key, rank in sorted(CAMPUSES, key=lambda item: len(item[0]), reverse=True):
        if key in blob:
            return rank
    return 40
