"""Copy CollegeDekho engineering facts from this PC to another database.

The catalogue on the server does not include these rows. They live in
engineering_facts and engineering_tables after the local CollegeDekho match.

On this PC, from the repo root:

    python db/engineering_transfer.py export output/engineering.json

Copy that file to the server, then from the repo root there:

    python db/engineering_transfer.py load output/engineering.json

The load replaces facts and tables for the colleges in the file. It does not
change college names, photos, or written sections. A slug that is not on the
server is skipped.
"""

import json
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.db import connect


def export_file(path):
    connection = connect()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT college_slug, source_slug, nirf_rank, fee_range,
                   average_package, ownership, approval, exams
            FROM engineering_facts
            ORDER BY college_slug
            """
        )
        facts = cursor.fetchall()
        cursor.execute(
            """
            SELECT college_slug, page, heading, columns, rows, display_order
            FROM engineering_tables
            ORDER BY college_slug, display_order
            """
        )
        tables = cursor.fetchall()
    connection.close()
    payload = {"facts": facts, "tables": tables}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    ranked = sum(1 for row in facts if row["nirf_rank"] is not None)
    print(f"Wrote {len(facts)} colleges, {ranked} with a NIRF rank, {len(tables)} tables")
    print(path)


def load_file(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    facts = payload["facts"]
    tables = payload["tables"]
    connection = connect()
    with connection.cursor() as cursor:
        cursor.execute("SELECT slug FROM colleges")
        known = {row["slug"] for row in cursor.fetchall()}
        kept = [row for row in facts if row["college_slug"] in known]
        missing = len(facts) - len(kept)
        slugs = [row["college_slug"] for row in kept]
        if slugs:
            cursor.execute(
                "DELETE FROM engineering_tables WHERE college_slug = ANY(%s)",
                (slugs,),
            )
        cursor.executemany(
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
            [
                (
                    row["college_slug"],
                    row["source_slug"],
                    row["nirf_rank"],
                    row["fee_range"],
                    row["average_package"],
                    row["ownership"],
                    row["approval"],
                    row["exams"],
                )
                for row in kept
            ],
        )
        kept_slugs = set(slugs)
        table_rows = [row for row in tables if row["college_slug"] in kept_slugs]
        cursor.executemany(
            """
            INSERT INTO engineering_tables (
                college_slug, page, heading, columns, rows, display_order
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row["college_slug"],
                    row["page"],
                    row["heading"],
                    Jsonb(row["columns"]),
                    Jsonb(row["rows"]),
                    row["display_order"],
                )
                for row in table_rows
            ],
        )
        cursor.execute(
            "SELECT COUNT(*)::int AS total FROM engineering_facts WHERE nirf_rank IS NOT NULL"
        )
        ranked = cursor.fetchone()["total"]
    connection.commit()
    connection.close()
    print(f"Loaded {len(kept)} colleges and {len(table_rows)} tables. Skipped {missing} missing colleges.")
    print(f"NIRF ranks now stored: {ranked}")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {"export", "load"}:
        raise SystemExit("Use: python db/engineering_transfer.py export output/engineering.json")
    path = Path(sys.argv[2])
    if sys.argv[1] == "export":
        export_file(path)
    else:
        load_file(path)


if __name__ == "__main__":
    main()
