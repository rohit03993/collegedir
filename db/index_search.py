"""Build the Typesense college index from the new catalogue tables.

Start Typesense, set TYPESENSE_API_KEY in .env, then from the repo root:

    python db/index_search.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.db import connect, database_name
from api.format import choose_fee, clean
from api.ranks import engineering_rank, listing_category
from api.search import COLLECTION, SLUG_ALIASES, client, recreate_collection

BATCH = 500


def grouped_fees(connection):
    grouped = defaultdict(list)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT college_slug, course_name, course_group, specialization, fee_amount, fee_type
            FROM course_fees
            """
        )
        for row in cursor:
            grouped[row["college_slug"]].append(row)
    return grouped


def display_fee(fees):
    return choose_fee(fees)


def branches_for(fees):
    values = []
    seen = set()
    for fee in fees:
        for key in ("course_name", "specialization"):
            value = clean(fee[key])
            if not value:
                continue
            marker = value.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            values.append(value)
    return values


def groups_for(fees):
    values = []
    seen = set()
    for fee in fees:
        value = clean(fee["course_group"])
        if not value:
            continue
        marker = value.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        values.append(value)
    return values


def document(college, fees):
    course_group, label = display_fee(fees)
    groups = groups_for(fees)
    branches = branches_for(fees)
    rank = engineering_rank(college["slug"], college["name"])
    category = listing_category(college["slug"], college["name"], clean(college["category"]))
    doc = {
        "id": college["slug"],
        "slug": college["slug"],
        "name": college["name"],
        "priority": college["priority"] or 0,
    }
    if rank is not None:
        doc["engineering_rank"] = rank
    for key, value in (
        ("city", clean(college["city"])),
        ("state", clean(college["state"])),
        ("type", clean(college["type"])),
        ("category", category),
        ("course_group", course_group),
        ("fee_label", label),
        ("image", clean(college["image_path"])),
    ):
        if value:
            doc[key] = value
    if groups:
        doc["course_groups"] = groups
    if branches:
        doc["branches"] = branches
    rating = college["rating"]
    if rating is not None and float(rating) > 0:
        doc["rating"] = float(rating)
    if college["established"]:
        doc["established"] = int(college["established"])
    alias = SLUG_ALIASES.get(college["slug"])
    if alias:
        doc["aliases"] = alias
    return doc


def import_batches(typesense, documents):
    imported = 0
    for start in range(0, len(documents), BATCH):
        batch = documents[start : start + BATCH]
        result = typesense.collections[COLLECTION].documents.import_(batch, {"action": "upsert"})
        lines = result.splitlines() if isinstance(result, str) else result
        for line in lines:
            if isinstance(line, str):
                item = json.loads(line)
            else:
                item = line
            if not item.get("success", True):
                raise RuntimeError(item.get("error") or "Typesense rejected a college document")
        imported += len(batch)
        print(f"indexed {imported}")
    return imported


def main():
    print(f"Indexing colleges from database {database_name()}")
    with connect() as connection:
        fees = grouped_fees(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT slug, name, city, state, type, category, rating, image_path,
                       priority, established
                FROM colleges
                WHERE is_active IS TRUE AND name IS NOT NULL
                ORDER BY slug
                """
            )
            colleges = cursor.fetchall()
    documents = [document(college, fees.get(college["slug"], [])) for college in colleges]
    typesense = client()
    recreate_collection(typesense)
    count = import_batches(typesense, documents)
    print(f"Indexed {count} colleges")


if __name__ == "__main__":
    main()
