from api.format import clean, named_label, public_html, public_text, shown_date


def _link(value):
    text = public_text(value)
    if not text or not text.startswith("https://") or "dekhocampus" in text.lower():
        return None
    return text


def _page(page, per_page):
    page = max(1, min(int(page or 1), 2000))
    per_page = max(1, min(int(per_page or 20), 400))
    return page, per_page, (page - 1) * per_page


def _categories(cursor, table, active_only=True):
    active = "is_active IS TRUE AND " if active_only else ""
    cursor.execute(
        f"""
        SELECT category, COUNT(*)::int AS count
        FROM {table}
        WHERE {active}category IS NOT NULL AND btrim(category) <> '' AND category !~ '^[0-9]+$'
        GROUP BY category
        ORDER BY count DESC, category
        LIMIT 12
        """
    )
    return [{"name": row["category"], "count": row["count"]} for row in cursor.fetchall()]


def _faqs(cursor, page_name, slug, name):
    cursor.execute(
        """
        SELECT question, answer
        FROM faqs
        WHERE is_active IS TRUE AND page = %s AND (item_slug = %s OR item_slug = %s)
        ORDER BY display_order NULLS LAST, question
        """,
        (page_name, slug, name),
    )
    answers = []
    for row in cursor.fetchall():
        question = public_text(row["question"])
        answer = public_html(row["answer"])
        if question and answer:
            answers.append({"question": question, "answer": answer})
    return answers


def list_exams(connection, q, category, page, per_page):
    page, per_page, offset = _page(page, per_page)
    query = (q or "").strip()[:80]
    category = clean(category)
    where = "WHERE is_active IS TRUE"
    values = []
    if query:
        where += " AND (name ILIKE %s OR full_name ILIKE %s OR category ILIKE %s)"
        like = f"%{query}%"
        values.extend([like, like, like])
    if category:
        where += " AND category = %s"
        values.append(category)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*)::int AS total FROM exams {where}", values)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT slug, name, full_name, category, exam_date, level
            FROM exams
            {where}
            ORDER BY is_top_exam DESC, priority DESC NULLS LAST, name
            LIMIT %s OFFSET %s
            """,
            [*values, per_page, offset],
        )
        items = [
            {
                "slug": row["slug"],
                "name": row["name"],
                "fullName": clean(row["full_name"]),
                "category": named_label(row["category"]),
                "level": clean(row["level"]),
                "date": shown_date(row["exam_date"]),
            }
            for row in cursor.fetchall()
        ]
        categories = _categories(cursor, "exams")
    return {"total": total, "query": query, "category": category, "categories": categories, "items": items}


def exam_detail(connection, slug):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM exams WHERE slug = %s AND is_active IS TRUE", (slug,))
        row = cursor.fetchone()
        if row is None:
            return None
        faqs = _faqs(cursor, "exams", row["slug"], row["name"])
    return {
        "slug": row["slug"],
        "name": row["name"],
        "fullName": clean(row["full_name"]),
        "category": named_label(row["category"]),
        "level": clean(row["level"]),
        "date": shown_date(row["exam_date"]),
        "mode": clean(row["mode"]),
        "eligibility": public_html(row["eligibility"]),
        "officialWebsite": _link(row["official_website"]),
        "summaryHtml": public_html(row["summary_content"]),
        "descriptionHtml": public_html(row["description"]),
        "patternHtml": public_html(row["exam_pattern"]),
        "applicationHtml": public_html(row["application_process"]),
        "datesHtml": public_html(row["dates_content"]),
        "resultHtml": public_html(row["result_content"]),
        "faqs": faqs,
    }


def list_courses(connection, q, category, page, per_page):
    page, per_page, offset = _page(page, per_page)
    query = (q or "").strip()[:80]
    category = clean(category)
    where = "WHERE 1 = 1"
    values = []
    if query:
        where += " AND (name ILIKE %s OR category ILIKE %s)"
        like = f"%{query}%"
        values.extend([like, like])
    if category:
        where += " AND category = %s"
        values.append(category)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*)::int AS total FROM courses {where}", values)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT slug, name, category, level, duration, mode
            FROM courses
            {where}
            ORDER BY name
            LIMIT %s OFFSET %s
            """,
            [*values, per_page, offset],
        )
        items = [
            {
                "slug": row["slug"],
                "name": row["name"],
                "category": clean(row["category"]),
                "level": clean(row["level"]),
                "duration": clean(row["duration"]),
                "mode": clean(row["mode"]),
            }
            for row in cursor.fetchall()
        ]
        categories = _categories(cursor, "courses", active_only=False)
    return {"total": total, "query": query, "category": category, "categories": categories, "items": items}


def course_detail(connection, slug):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM courses WHERE slug = %s", (slug,))
        row = cursor.fetchone()
        if row is None:
            return None
        faqs = _faqs(cursor, "courses", row["slug"], row["name"])
    return {
        "slug": row["slug"],
        "name": row["name"],
        "category": clean(row["category"]),
        "level": clean(row["level"]),
        "duration": clean(row["duration"]),
        "mode": clean(row["mode"]),
        "eligibility": public_text(row["eligibility"]),
        "summary": public_text(row["short_description"]),
        "descriptionHtml": public_html(row["description"]),
        "aboutHtml": public_html(row["about_content"]),
        "admissionHtml": public_html(row["admission_process"]),
        "subjectsHtml": public_html(row["subjects_content"]),
        "scopeHtml": public_html(row["scope_content"]),
        "faqs": faqs,
    }


def list_articles(connection, q, page, per_page):
    page, per_page, offset = _page(page, per_page)
    query = (q or "").strip()[:80]
    where = "WHERE is_active IS TRUE"
    values = []
    if query:
        where += " AND (title ILIKE %s OR description ILIKE %s OR category ILIKE %s)"
        like = f"%{query}%"
        values.extend([like, like, like])
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*)::int AS total FROM articles {where}", values)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT slug, title, description, category, author, published_at
            FROM articles
            {where}
            ORDER BY published_at DESC NULLS LAST, title
            LIMIT %s OFFSET %s
            """,
            [*values, per_page, offset],
        )
        items = [
            {
                "slug": row["slug"],
                "title": row["title"],
                "description": public_text(row["description"]),
                "category": clean(row["category"]),
                "author": public_text(row["author"]),
            }
            for row in cursor.fetchall()
        ]
    return {"total": total, "query": query, "items": items}


def article_detail(connection, slug):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM articles WHERE slug = %s AND is_active IS TRUE", (slug,))
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "slug": row["slug"],
        "title": row["title"],
        "description": public_text(row["description"]),
        "category": clean(row["category"]),
        "author": public_text(row["author"]),
        "contentHtml": public_html(row["content"]),
    }


def list_scholarships(connection, q, page, per_page):
    page, per_page, offset = _page(page, per_page)
    query = (q or "").strip()[:80]
    where = "WHERE is_active IS TRUE"
    values = []
    if query:
        where += " AND (title ILIKE %s OR provider ILIKE %s OR category ILIKE %s)"
        like = f"%{query}%"
        values.extend([like, like, like])
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*)::int AS total FROM scholarships {where}", values)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT slug, title, provider, amount, deadline, category, level
            FROM scholarships
            {where}
            ORDER BY title
            LIMIT %s OFFSET %s
            """,
            [*values, per_page, offset],
        )
        items = [
            {
                "slug": row["slug"],
                "title": row["title"],
                "provider": clean(row["provider"]),
                "amount": clean(row["amount"]),
                "deadline": clean(row["deadline"]),
                "category": clean(row["category"]),
                "level": clean(row["level"]),
            }
            for row in cursor.fetchall()
        ]
    return {"total": total, "query": query, "items": items}


def scholarship_detail(connection, slug):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM scholarships WHERE slug = %s AND is_active IS TRUE", (slug,))
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "slug": row["slug"],
        "title": row["title"],
        "provider": clean(row["provider"]),
        "amount": clean(row["amount"]),
        "deadline": clean(row["deadline"]),
        "category": clean(row["category"]),
        "level": clean(row["level"]),
        "eligibilityHtml": public_html(row["eligibility"]),
        "descriptionHtml": public_html(row["description"]),
        "applyUrl": _link(row["apply_url"]),
    }
