from urllib.parse import urlencode

from api.format import (
    choose_fee,
    clean,
    fee_label,
    named_label,
    public_html,
    public_text,
    rating_value,
    shown_date,
)

PREFERRED_COURSES = ("B.E. / B.Tech", "MBBS", "MBA / PGDM")
STATUS_TAGS = {"official refresh pending"}


def colleges_link(**params):
    pairs = [(key, value) for key, value in params.items() if value]
    query = urlencode(pairs)
    return "/colleges" + (f"?{query}" if query else "")


def local_path(value):
    if isinstance(value, str) and value.startswith("/media/"):
        return value
    return None


def gallery_photos(college):
    hero_source = college["image_url"] if isinstance(college["image_url"], str) else None
    photos = []
    for index, url in enumerate(college["gallery"] or [], 1):
        if not isinstance(url, str):
            continue
        item = url.strip()
        if item.startswith("/media/"):
            photos.append(item.split("?", 1)[0])
        elif item.startswith("https://") and item != hero_source:
            photos.append(f"/media/colleges/{college['slug']}/gallery-{index}")
    if photos:
        return photos
    return [path for path in (college["gallery_paths"] or []) if local_path(path)]


def photo_url(slug, image_path, image_url, kind="hero"):
    saved = local_path(image_path)
    if saved:
        return saved
    if isinstance(image_url, str) and image_url.startswith("https://"):
        return f"/media/colleges/{slug}/{kind}"
    return None


def visible_tags(category, city, state, tags):
    skip = {value.casefold() for value in (category, city, state) if value}
    skip.update(STATUS_TAGS)
    visible = []
    for tag in tags or []:
        text = public_text(tag) if isinstance(tag, str) else None
        if not text or text.casefold() in skip:
            continue
        visible.append(text)
    return visible


def card(slug, name, city, state, ownership, fees, rating, image_path, image_url):
    group, label = choose_fee(fees)
    return {
        "slug": slug,
        "name": name,
        "city": clean(city),
        "state": clean(state),
        "ownership": clean(ownership),
        "courseGroup": group,
        "fee": label,
        "rating": rating_value(rating),
        "image": photo_url(slug, image_path, image_url),
    }


def home_payload(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT category AS name, COUNT(*)::int AS count
            FROM colleges
            WHERE is_active IS TRUE AND category IS NOT NULL AND btrim(category) <> ''
            GROUP BY category
            ORDER BY COUNT(*) DESC, category
            """
        )
        streams = [
            {"name": row["name"], "count": row["count"], "href": colleges_link(stream=row["name"])}
            for row in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT course_group AS name, COUNT(DISTINCT college_slug)::int AS count
            FROM course_fees
            WHERE course_group IS NOT NULL AND btrim(course_group) <> ''
            GROUP BY course_group
            ORDER BY COUNT(DISTINCT college_slug) DESC, course_group
            """
        )
        groups = cursor.fetchall()
        cursor.execute(
            """
            SELECT slug, name, city, state, type, rating, image_path, image_url
            FROM colleges
            WHERE is_active IS TRUE
            ORDER BY featured_rank ASC NULLS LAST, priority DESC NULLS LAST, name ASC
            LIMIT 8
            """
        )
        colleges = cursor.fetchall()
        slugs = [row["slug"] for row in colleges]
        fee_map = {}
        if slugs:
            cursor.execute(
                """
                SELECT college_slug, course_group, fee_amount, fee_type
                FROM course_fees
                WHERE college_slug = ANY(%s)
                """,
                (slugs,),
            )
            for fee in cursor.fetchall():
                fee_map.setdefault(fee["college_slug"], []).append(fee)
        cursor.execute(
            """
            SELECT slug, name, category, exam_date
            FROM exams
            WHERE is_active IS TRUE AND name IS NOT NULL
            ORDER BY is_top_exam DESC, priority DESC NULLS LAST, name ASC
            LIMIT 8
            """
        )
        exams = cursor.fetchall()

    names = {row["name"] for row in groups}
    ordered = [name for name in PREFERRED_COURSES if name in names]
    for row in groups:
        if row["name"] not in ordered:
            ordered.append(row["name"])
        if len(ordered) >= 6:
            break

    cards = [
        card(
            college["slug"],
            college["name"],
            college["city"],
            college["state"],
            college["type"],
            fee_map.get(college["slug"], []),
            college["rating"],
            college["image_path"],
            college["image_url"],
        )
        for college in colleges
    ]
    exam_cards = []
    for exam in exams:
        exam_cards.append(
            {
                "name": exam["name"],
                "category": named_label(exam["category"]),
                "date": shown_date(exam["exam_date"]),
                "href": f"/exams/{exam['slug']}",
            }
        )
    return {
        "suggestions": [{"label": name, "href": colleges_link(course=name)} for name in ordered[:6]],
        "streams": streams,
        "next": streams[:4],
        "colleges": cards,
        "exams": exam_cards,
    }


def apply_photos(connection, cards):
    slugs = [card["slug"] for card in cards if card.get("slug")]
    if not slugs:
        return cards
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT slug, image_url, image_path
            FROM colleges
            WHERE slug = ANY(%s)
            """,
            (slugs,),
        )
        found = {row["slug"]: row for row in cursor.fetchall()}
    for card in cards:
        row = found.get(card["slug"])
        card["image"] = (
            photo_url(row["slug"], row["image_path"], row["image_url"]) if row else None
        )
    return cards


def fee_rows(rows):
    listed = []
    for row in rows:
        name = public_text(row["course_name"])
        specialization = public_text(row["specialization"])
        if specialization and name and specialization.casefold() == name.casefold():
            specialization = None
        group = public_text(row["course_group"])
        duration = public_text(row["duration"])
        year = public_text(row["year"])
        fee = fee_label(row["fee_amount"], row["fee_type"])
        if not any((name, specialization, group, duration, fee)):
            continue
        listed.append(
            {
                "courseName": name,
                "courseGroup": group,
                "specialization": specialization,
                "duration": duration,
                "year": year,
                "fee": fee,
            }
        )
    return listed


def college_payload(connection, slug):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM colleges
            WHERE slug = %s AND is_active IS TRUE
            """,
            (slug,),
        )
        college = cursor.fetchone()
        if college is None:
            return None
        cursor.execute(
            """
            SELECT course_name, course_group, specialization, duration, fee_amount, fee_type, year
            FROM course_fees
            WHERE college_slug = %s
            ORDER BY course_group NULLS LAST, course_name NULLS LAST
            """,
            (slug,),
        )
        fees = cursor.fetchall()
        cursor.execute(
            """
            SELECT question, answer
            FROM faqs
            WHERE is_active IS TRUE AND page = 'colleges' AND item_slug = %s
            ORDER BY display_order NULLS LAST, question
            """,
            (slug,),
        )
        faqs = cursor.fetchall()
        facts = engineering_facts(cursor, slug)

    image = photo_url(college["slug"], college["image_path"], college["image_url"])
    gallery = gallery_photos(college)
    reviews = college["reviews"] if isinstance(college["reviews"], int) and college["reviews"] > 0 else None
    answers = []
    for faq in faqs:
        question = public_text(faq["question"])
        answer = public_html(faq["answer"])
        if question and answer:
            answers.append({"question": question, "answer": answer})
    approvals = [text for text in (public_text(item) for item in (college["approvals"] or [])) if text]
    return {
        "slug": college["slug"],
        "name": college["name"],
        "city": clean(college["city"]),
        "state": clean(college["state"]),
        "ownership": clean(college["type"]),
        "established": college["established"],
        "category": clean(college["category"]),
        "tags": visible_tags(college["category"], college["city"], college["state"], college["tags"]),
        "approvals": approvals,
        "rating": rating_value(college["rating"]),
        "reviews": reviews,
        "image": image,
        "logo": photo_url(college["slug"], college["logo_path"], college["logo_url"], "logo"),
        "gallery": gallery,
        "overviewHtml": public_html(college["description"]),
        "feesText": public_text(college["fees_text"]),
        "fees": fee_rows(fees),
        "admissionHtml": public_html(college["admission_process"]),
        "cutoffHtml": public_html(college["cutoff"]),
        "placementHtml": public_html(college["placement_content"]),
        "facilitiesHtml": public_html(college["facilities_content"]),
        "hostelHtml": public_html(college["hostel_life"]),
        "faqs": answers,
        "facts": facts,
    }


def engineering_facts(cursor, slug):
    grouped = {page: [] for page in ("courses", "admission", "placement", "cutoff", "scholarship")}
    cursor.execute(
        """
        SELECT nirf_rank, fee_range, average_package, approval, exams
        FROM engineering_facts
        WHERE college_slug = %s
        """,
        (slug,),
    )
    row = cursor.fetchone()
    cursor.execute(
        """
        SELECT page, heading, columns, rows
        FROM engineering_tables
        WHERE college_slug = %s
        ORDER BY display_order
        """,
        (slug,),
    )
    for table in cursor.fetchall():
        if table["page"] not in grouped:
            continue
        grouped[table["page"]].append(
            {
                "heading": table["heading"],
                "columns": table["columns"] or [],
                "rows": table["rows"] or [],
            }
        )
    return {
        "nirfRank": row["nirf_rank"] if row else None,
        "feeRange": clean(row["fee_range"]) if row else None,
        "averagePackage": clean(row["average_package"]) if row else None,
        "approval": clean(row["approval"]) if row else None,
        "exams": clean(row["exams"]) if row else None,
        **grouped,
    }
