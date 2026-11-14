"""Copy saved CollegeDekho engineering facts into admission_setu1.

One college:

    python db/import_collegedekho.py iit-delhi

Every college that matches the catalogue:

    python db/import_collegedekho.py --all

Only the colleges skipped last time, onto records that have no facts yet:

    python db/import_collegedekho.py --remaining
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.db import connect
from db.collegedekho import parse_college
from db.match_collegedekho import load_listing, match_by_search, match_cards, match_existing

ALIASES = {
    "iit-delhi": "indian-institute-of-technology-iit-new-delhi",
}

STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS engineering_facts (
        college_slug text PRIMARY KEY REFERENCES colleges (slug),
        source_slug text NOT NULL,
        nirf_rank integer,
        fee_range text,
        average_package text,
        ownership text,
        approval text,
        exams text
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS engineering_tables (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        college_slug text NOT NULL REFERENCES colleges (slug),
        page text NOT NULL,
        heading text,
        columns jsonb NOT NULL,
        rows jsonb NOT NULL,
        display_order integer NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS engineering_tables_college_idx
    ON engineering_tables (college_slug, display_order)
    """,
)


def ensure_tables(connection):
    with connection.cursor() as cursor:
        for statement in STATEMENTS:
            cursor.execute(statement)
    connection.commit()


def save_pair(cursor, source_slug, college_slug):
    facts, tables = parse_college(source_slug)
    cursor.execute("DELETE FROM engineering_tables WHERE college_slug = %s", (college_slug,))
    cursor.execute(
        """
        INSERT INTO engineering_facts (
            college_slug, source_slug, nirf_rank, fee_range, average_package,
            ownership, approval, exams
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (college_slug) DO UPDATE SET
            source_slug = EXCLUDED.source_slug,
            nirf_rank = EXCLUDED.nirf_rank,
            fee_range = EXCLUDED.fee_range,
            average_package = EXCLUDED.average_package,
            ownership = EXCLUDED.ownership,
            approval = EXCLUDED.approval,
            exams = EXCLUDED.exams
        """,
        (
            college_slug,
            facts["source_slug"],
            facts["nirf_rank"],
            facts["fee_range"],
            facts["average_package"],
            facts["ownership"],
            facts["approval"],
            facts["exams"],
        ),
    )
    cursor.executemany(
        """
        INSERT INTO engineering_tables (
            college_slug, page, heading, columns, rows, display_order
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            (
                college_slug,
                table["page"],
                table["heading"],
                json.dumps(table["columns"]),
                json.dumps(table["rows"]),
                order,
            )
            for order, table in enumerate(tables)
        ],
    )
    return facts, len(tables)


def catalogue(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT slug, name, city, state, category
            FROM colleges
            WHERE is_active IS TRUE
            """
        )
        return cursor.fetchall()


def import_all(connection):
    cards = load_listing()
    reserved = set(ALIASES.values())
    colleges = [college for college in catalogue(connection) if college["slug"] not in reserved]
    remaining = [card for card in cards if card["slug"] not in ALIASES]
    matched, skipped = match_cards(colleges, remaining)
    pairs = list(ALIASES.items()) + matched
    print(f"Matched {len(pairs)} colleges. Skipped {len(skipped)}.", flush=True)
    loaded = 0
    failed = 0
    with connection.cursor() as cursor:
        for number, (source_slug, college_slug) in enumerate(pairs, start=1):
            try:
                cursor.execute("SAVEPOINT college_import")
                save_pair(cursor, source_slug, college_slug)
                cursor.execute("RELEASE SAVEPOINT college_import")
                loaded += 1
            except Exception as exc:
                cursor.execute("ROLLBACK TO SAVEPOINT college_import")
                failed += 1
                print(f"FAILED {source_slug}: {exc}", flush=True)
                continue
            if number % 25 == 0:
                connection.commit()
                print(f"loaded {loaded}", flush=True)
        connection.commit()
    report = ROOT / "output"
    report.mkdir(exist_ok=True)
    (report / "collegedekho_unmatched.txt").write_text("\n".join(skipped), encoding="utf-8")
    print(f"Finished. Loaded {loaded}. Failed {failed}. Unmatched list: output/collegedekho_unmatched.txt", flush=True)


def import_remaining(connection):
    """Attach skipped CollegeDekho cards to colleges that have no facts yet."""
    cards = load_listing()
    with connection.cursor() as cursor:
        cursor.execute("SELECT college_slug, source_slug FROM engineering_facts")
        filled = cursor.fetchall()
    taken = {row["college_slug"] for row in filled}
    seen_sources = {row["source_slug"] for row in filled}
    colleges = catalogue(connection)
    remaining = [card for card in cards if card["slug"] not in seen_sources]
    by_source = {card["slug"]: card for card in remaining}
    matched, skipped = match_existing(colleges, remaining)
    kept = []
    for source_slug, college_slug in matched:
        if college_slug in taken:
            skipped.append(by_source[source_slug].get("college_name") or source_slug)
            continue
        kept.append((source_slug, college_slug))
    write_matches(connection, kept, skipped)


def import_search(connection):
    """Copy CollegeDekho facts when site search finds exactly one college."""
    cards = load_listing()
    with connection.cursor() as cursor:
        cursor.execute("SELECT college_slug, source_slug FROM engineering_facts")
        filled = cursor.fetchall()
    taken = {row["college_slug"] for row in filled}
    seen_sources = {row["source_slug"] for row in filled}
    remaining = [card for card in cards if card["slug"] not in seen_sources]
    found, skipped = match_by_search(remaining, taken)
    write_matches(connection, [(source, dest) for source, dest, _score in found], skipped)


def write_matches(connection, matched, skipped):
    print(f"New matches {len(matched)}. Still skipped {len(skipped)}.", flush=True)
    loaded = 0
    failed = 0
    with connection.cursor() as cursor:
        for number, (source_slug, college_slug) in enumerate(matched, start=1):
            try:
                cursor.execute("SAVEPOINT college_import")
                save_pair(cursor, source_slug, college_slug)
                cursor.execute("RELEASE SAVEPOINT college_import")
                loaded += 1
            except Exception as exc:
                cursor.execute("ROLLBACK TO SAVEPOINT college_import")
                failed += 1
                print(f"FAILED {source_slug}: {exc}", flush=True)
                continue
            if number % 25 == 0:
                connection.commit()
                print(f"loaded {loaded}", flush=True)
        connection.commit()
    report = ROOT / "output"
    report.mkdir(exist_ok=True)
    (report / "collegedekho_unmatched.txt").write_text("\n".join(skipped), encoding="utf-8")
    print(f"Finished. Loaded {loaded}. Failed {failed}. Unmatched list: output/collegedekho_unmatched.txt", flush=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python db/import_collegedekho.py iit-delhi"
            "   or   python db/import_collegedekho.py --all"
            "   or   python db/import_collegedekho.py --remaining"
            "   or   python db/import_collegedekho.py --search"
        )
    with connect() as connection:
        ensure_tables(connection)
        if sys.argv[1] == "--all":
            import_all(connection)
            return
        if sys.argv[1] == "--remaining":
            import_remaining(connection)
            return
        if sys.argv[1] == "--search":
            import_search(connection)
            return
        source_slug = sys.argv[1].strip()
        college_slug = ALIASES.get(source_slug)
        if not college_slug:
            matched, _skipped = match_cards(catalogue(connection), [{"slug": source_slug, "college_name": source_slug, "city": ""}])
            if not matched:
                raise SystemExit(f"No Admission Setu match for {source_slug}")
            college_slug = matched[0][1]
        with connection.cursor() as cursor:
            facts, count = save_pair(cursor, source_slug, college_slug)
        connection.commit()
    print(f"Loaded {source_slug} onto {college_slug}: {count} tables, NIRF {facts['nirf_rank']}")


if __name__ == "__main__":
    main()
