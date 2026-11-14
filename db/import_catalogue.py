"""Load dekho-campus JSONL files into the new Admission Setu database.

This script does not create the database. Create an empty database, apply
db/schema.sql, then from the repo root run:

    python db/import_catalogue.py

Empty source fields are stored as empty. Photo files are not downloaded here.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psycopg.types.json import Json

from api.db import connect, database_name
from api.format import clean, positive_int, text_list
from api.ranks import listing_category

DATA = ROOT / "dekho-campus"
BATCH = 200


def records(filename):
    path = DATA / filename
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping broken JSON in {filename} line {line_number}")


def chunks(rows):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH:
            yield batch
            batch = []
    if batch:
        yield batch


def flag(value, default=True):
    if value is None:
        return default
    return bool(value)


def jsonb(value):
    return Json(value) if value else None


def optional_number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def load_states(connection):
    rows = []
    for item in records("states_cities.jsonl"):
        state = clean(item.get("state"))
        city = clean(item.get("city"))
        item_id = clean(item.get("id"))
        if not item_id or not state or not city:
            continue
        rows.append((item_id, state, city, flag(item.get("is_active"), True)))
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE states_cities")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO states_cities (id, state, city, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    state = EXCLUDED.state,
                    city = EXCLUDED.city,
                    is_active = EXCLUDED.is_active
                """,
                batch,
            )
    connection.commit()
    print(f"states_cities {len(rows)}")


def load_courses(connection):
    rows = []
    seen = set()
    for item in records("courses.jsonl"):
        slug = clean(item.get("slug"))
        name = clean(item.get("name"))
        if not slug or not name or slug in seen:
            continue
        seen.add(slug)
        rows.append(
            (
                slug,
                name,
                clean(item.get("category")),
                clean(item.get("level")),
                clean(item.get("duration")),
                clean(item.get("eligibility")),
                clean(item.get("short_description")),
                clean(item.get("description")),
                clean(item.get("about_content")),
                clean(item.get("admission_process")),
                clean(item.get("subjects_content")),
                clean(item.get("scope_content")),
                clean(item.get("mode")),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE courses")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO courses (
                    slug, name, category, level, duration, eligibility, short_description,
                    description, about_content, admission_process, subjects_content, scope_content, mode
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    level = EXCLUDED.level,
                    duration = EXCLUDED.duration,
                    eligibility = EXCLUDED.eligibility,
                    short_description = EXCLUDED.short_description,
                    description = EXCLUDED.description,
                    about_content = EXCLUDED.about_content,
                    admission_process = EXCLUDED.admission_process,
                    subjects_content = EXCLUDED.subjects_content,
                    scope_content = EXCLUDED.scope_content,
                    mode = EXCLUDED.mode
                """,
                batch,
            )
    connection.commit()
    print(f"courses {len(rows)}")


def college_row(item):
    slug = clean(item.get("slug"))
    name = clean(item.get("name"))
    if not slug or not name:
        return None
    gallery = text_list(item.get("gallery_images")) or text_list(item.get("carousel_images"))
    return (
        slug,
        name,
        clean(item.get("city")),
        clean(item.get("state")),
        clean(item.get("type")),
        listing_category(slug, name, clean(item.get("category"))),
        optional_number(item.get("rating")) if optional_number(item.get("rating")) else (
            0 if item.get("rating") in (0, 0.0, "0") else None
        ),
        positive_int(item.get("reviews")) or (0 if item.get("reviews") in (0, "0") else None),
        clean(item.get("fees")),
        clean(item.get("image")),
        clean(item.get("logo")),
        jsonb(text_list(item.get("approvals"))),
        positive_int(item.get("established")),
        clean(item.get("description")),
        clean(item.get("admission_process")),
        clean(item.get("cutoff")),
        clean(item.get("placement_content")),
        clean(item.get("facilities_content")),
        clean(item.get("hostel_life")),
        jsonb(gallery),
        jsonb(text_list(item.get("tags"))),
        positive_int(item.get("priority")),
        positive_int(item.get("featured_rank")),
        flag(item.get("is_active"), True),
    )


COLLEGE_SQL = """
INSERT INTO colleges (
    slug, name, city, state, type, category, rating, reviews, fees_text,
    image_url, logo_url, approvals, established, description, admission_process,
    cutoff, placement_content, facilities_content, hostel_life, gallery, tags,
    priority, featured_rank, is_active
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s
)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    type = EXCLUDED.type,
    category = EXCLUDED.category,
    rating = EXCLUDED.rating,
    reviews = EXCLUDED.reviews,
    fees_text = EXCLUDED.fees_text,
    image_url = EXCLUDED.image_url,
    logo_url = EXCLUDED.logo_url,
    approvals = EXCLUDED.approvals,
    established = EXCLUDED.established,
    description = EXCLUDED.description,
    admission_process = EXCLUDED.admission_process,
    cutoff = EXCLUDED.cutoff,
    placement_content = EXCLUDED.placement_content,
    facilities_content = EXCLUDED.facilities_content,
    hostel_life = EXCLUDED.hostel_life,
    gallery = EXCLUDED.gallery,
    tags = EXCLUDED.tags,
    priority = EXCLUDED.priority,
    featured_rank = EXCLUDED.featured_rank,
    is_active = EXCLUDED.is_active
"""


def load_colleges(connection):
    seen = set()
    count = 0
    with connection.cursor() as cursor:
        batch = []
        for item in records("colleges.jsonl"):
            row = college_row(item)
            if row is None or row[0] in seen:
                continue
            seen.add(row[0])
            batch.append(row)
            if len(batch) >= BATCH:
                cursor.executemany(COLLEGE_SQL, batch)
                count += len(batch)
                batch = []
                connection.commit()
        if batch:
            cursor.executemany(COLLEGE_SQL, batch)
            count += len(batch)
        if seen:
            cursor.execute("DELETE FROM colleges WHERE NOT (slug = ANY(%s))", (list(seen),))
    connection.commit()
    print(f"colleges {count}")


def load_fees(connection):
    rows = []
    seen = set()
    for item in records("course_fees.jsonl"):
        item_id = clean(item.get("id"))
        college_slug = clean(item.get("college_slug"))
        if not item_id or not college_slug or item_id in seen:
            continue
        seen.add(item_id)
        rows.append(
            (
                item_id,
                college_slug,
                clean(item.get("course_slug")),
                clean(item.get("course_name")),
                clean(item.get("course_group")),
                clean(item.get("specialization")),
                clean(item.get("academic_level")),
                clean(item.get("duration")),
                optional_number(item.get("fee_amount")),
                clean(item.get("fee_type")),
                clean(item.get("year")),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE course_fees")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO course_fees (
                    id, college_slug, course_slug, course_name, course_group,
                    specialization, academic_level, duration, fee_amount, fee_type, year
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                batch,
            )
    connection.commit()
    print(f"course_fees {len(rows)}")


def load_exams(connection):
    rows = []
    seen = set()
    for item in records("exams.jsonl"):
        slug = clean(item.get("slug"))
        name = clean(item.get("name"))
        if not slug or not name or slug in seen:
            continue
        seen.add(slug)
        rows.append(
            (
                slug,
                name,
                clean(item.get("full_name")),
                clean(item.get("category")),
                clean(item.get("exam_date")),
                flag(item.get("is_top_exam"), False),
                flag(item.get("is_active"), True),
                positive_int(item.get("priority")),
                clean(item.get("level")),
                clean(item.get("eligibility")),
                clean(item.get("mode")),
                clean(item.get("description")),
                clean(item.get("summary_content")),
                clean(item.get("application_process")),
                clean(item.get("exam_pattern")),
                clean(item.get("dates_content")),
                clean(item.get("result_content")),
                clean(item.get("official_website")),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE exams")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO exams (
                    slug, name, full_name, category, exam_date, is_top_exam, is_active, priority,
                    level, eligibility, mode, description, summary_content, application_process,
                    exam_pattern, dates_content, result_content, official_website
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                batch,
            )
    connection.commit()
    print(f"exams {len(rows)}")


def load_faqs(connection):
    rows = []
    seen = set()
    for item in records("faqs.jsonl"):
        item_id = clean(item.get("id"))
        question = clean(item.get("question"))
        if not item_id or not question or item_id in seen:
            continue
        seen.add(item_id)
        rows.append(
            (
                item_id,
                question,
                clean(item.get("answer")),
                clean(item.get("page")),
                clean(item.get("item_slug")),
                positive_int(item.get("display_order")) or 0,
                flag(item.get("is_active"), True),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE faqs")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO faqs (id, question, answer, page, item_slug, display_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                batch,
            )
    connection.commit()
    print(f"faqs {len(rows)}")


def load_articles(connection):
    rows = []
    seen = set()
    for item in records("articles.jsonl"):
        slug = clean(item.get("slug"))
        title = clean(item.get("title"))
        if not slug or not title or slug in seen:
            continue
        if item.get("status") != "Published" or not flag(item.get("is_active"), True):
            continue
        seen.add(slug)
        rows.append(
            (
                slug,
                title,
                clean(item.get("description")),
                clean(item.get("content")),
                clean(item.get("category")),
                clean(item.get("author")),
                clean(item.get("created_at")),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE articles")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO articles (slug, title, description, content, category, author, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                batch,
            )
    connection.commit()
    print(f"articles {len(rows)}")


def load_scholarships(connection):
    rows = []
    seen = set()
    for item in records("scholarships.jsonl"):
        slug = clean(item.get("slug"))
        title = clean(item.get("title"))
        if not slug or not title or slug in seen:
            continue
        if not flag(item.get("is_active"), False) and not flag(item.get("is_live"), False):
            continue
        seen.add(slug)
        rows.append(
            (
                slug,
                title,
                clean(item.get("provider")),
                clean(item.get("amount")),
                clean(item.get("eligibility")),
                clean(item.get("deadline")),
                clean(item.get("category")),
                clean(item.get("level")),
                clean(item.get("description")),
                clean(item.get("apply_url")),
            )
        )
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE scholarships")
        for batch in chunks(rows):
            cursor.executemany(
                """
                INSERT INTO scholarships (
                    slug, title, provider, amount, eligibility, deadline, category, level, description, apply_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                batch,
            )
    connection.commit()
    print(f"scholarships {len(rows)}")


def main():
    print(f"Importing catalogue into database {database_name()}")
    with connect() as connection:
        load_states(connection)
        load_courses(connection)
        load_colleges(connection)
        load_fees(connection)
        load_exams(connection)
        load_faqs(connection)
        load_articles(connection)
        load_scholarships(connection)
    print("Import finished. College photos and the search index are left as they are.")


if __name__ == "__main__":
    main()
