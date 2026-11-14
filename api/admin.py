"""Admin college editor and staff accounts."""

import re

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.types.json import Jsonb

from api.auth import check_password, expiry, hash_password, new_token
from api.db import connect
from api.format import clean

router = APIRouter(prefix="/api/admin")
PAGE_SIZE = 20
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SORTS = {
    "name": "c.name ASC",
    "priority": "c.priority DESC NULLS LAST, c.name ASC",
    "state": "c.state ASC NULLS LAST, c.name ASC",
    "nirf": "f.nirf_rank ASC NULLS LAST, c.name ASC",
}
TEXT = {
    "city": "city",
    "state": "state",
    "type": "type",
    "category": "category",
    "feesText": "fees_text",
    "imageUrl": "image_url",
    "logoUrl": "logo_url",
    "imagePath": "image_path",
    "logoPath": "logo_path",
    "description": "description",
    "admission": "admission_process",
    "cutoff": "cutoff",
    "placement": "placement_content",
    "facilities": "facilities_content",
    "hostel": "hostel_life",
}


def connection():
    try:
        opened = connect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not available.") from exc
    try:
        yield opened
    finally:
        opened.close()


def _blank(value):
    if value is None:
        return ""
    return str(value)


def _lines(value):
    if not isinstance(value, list):
        return ""
    return "\n".join(str(item).strip() for item in value if str(item).strip())


def _split(value):
    items = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    return items or None


def _whole(value, label):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc


def _decimal(value, label):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a number.") from exc


def _slug(value):
    text = str(value or "").strip().lower()
    if not SLUG.match(text):
        raise ValueError("Slug can use lowercase letters, numbers, and hyphens.")
    return text


def _email(value):
    text = str(value or "").strip().lower()
    if "@" not in text or " " in text or len(text) > 200:
        raise ValueError("Enter a valid email.")
    return text


def _password(value):
    text = str(value or "")
    if len(text) < 8:
        raise ValueError("Use a password of at least 8 characters.")
    return text


def staff_count(db):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*)::int AS total FROM staff")
            total = cursor.fetchone()["total"]
    except psycopg.errors.UndefinedTable:
        db.rollback()
        return None
    return total


def current_staff(authorization: str = Header(default=""), db=Depends(connection)):
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token == authorization:
        raise HTTPException(status_code=401, detail="Sign in again.")
    with db.cursor() as cursor:
        try:
            cursor.execute(
                """
                SELECT s.id, s.email, s.name, s.role, s.is_active
                FROM staff_sessions n
                JOIN staff s ON s.id = n.staff_id
                WHERE n.token = %s AND n.expires_at > now()
                """,
                (token,),
            )
        except psycopg.errors.UndefinedTable:
            db.rollback()
            raise HTTPException(status_code=503, detail="Apply db/admin.sql before using the admin.")
        row = cursor.fetchone()
    if row is None or not row["is_active"]:
        raise HTTPException(status_code=401, detail="Sign in again.")
    return row


def require_admin(staff=Depends(current_staff)):
    if staff["role"] != "admin":
        raise HTTPException(status_code=403, detail="An admin account is required for team access.")
    return staff


def _public(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
    }


def college_form(row, facts):
    facts = facts or {}
    return {
        "name": _blank(row["name"]),
        "slug": row["slug"],
        "active": bool(row["is_active"]),
        "city": _blank(row["city"]),
        "state": _blank(row["state"]),
        "type": _blank(row["type"]),
        "category": _blank(row["category"]),
        "established": _blank(row["established"]),
        "priority": _blank(row["priority"]),
        "featuredRank": _blank(row["featured_rank"]),
        "rating": _blank(row["rating"]),
        "reviews": _blank(row["reviews"]),
        "feesText": _blank(row["fees_text"]),
        "imageUrl": _blank(row["image_url"]),
        "logoUrl": _blank(row["logo_url"]),
        "imagePath": _blank(row["image_path"]),
        "logoPath": _blank(row["logo_path"]),
        "approvals": _lines(row["approvals"]),
        "gallery": _lines(row["gallery"]),
        "tags": _lines(row["tags"]),
        "description": _blank(row["description"]),
        "admission": _blank(row["admission_process"]),
        "cutoff": _blank(row["cutoff"]),
        "placement": _blank(row["placement_content"]),
        "facilities": _blank(row["facilities_content"]),
        "hostel": _blank(row["hostel_life"]),
        "nirfRank": _blank(facts.get("nirf_rank")),
        "feeRange": _blank(facts.get("fee_range")),
        "averagePackage": _blank(facts.get("average_package")),
        "ownership": _blank(facts.get("ownership")),
        "approval": _blank(facts.get("approval")),
        "exams": _blank(facts.get("exams")),
    }


def _load(cursor, slug):
    cursor.execute("SELECT * FROM colleges WHERE slug = %s", (slug,))
    row = cursor.fetchone()
    if row is None:
        return None, None
    cursor.execute("SELECT * FROM engineering_facts WHERE college_slug = %s", (slug,))
    return row, cursor.fetchone()


def _move_slug(cursor, old, new):
    cursor.execute("SELECT 1 FROM colleges WHERE slug = %s", (new,))
    if cursor.fetchone():
        raise ValueError("That slug is already used.")
    cursor.execute("SELECT * FROM colleges WHERE slug = %s", (old,))
    current = cursor.fetchone()
    columns = [key for key in current.keys() if key != "slug"]
    listed = ", ".join(f'"{key}"' for key in columns)
    cursor.execute(
        f"INSERT INTO colleges (slug, {listed}) SELECT %s, {listed} FROM colleges WHERE slug = %s",
        (new, old),
    )
    for table in ("course_fees", "engineering_facts", "engineering_tables"):
        cursor.execute(
            f"UPDATE {table} SET college_slug = %s WHERE college_slug = %s",
            (new, old),
        )
    cursor.execute(
        "UPDATE faqs SET item_slug = %s WHERE item_slug = %s AND page = 'colleges'",
        (new, old),
    )
    cursor.execute("DELETE FROM colleges WHERE slug = %s", (old,))


def _save_facts(cursor, slug, body):
    values = (
        _whole(body.get("nirfRank"), "NIRF rank"),
        clean(body.get("feeRange")),
        clean(body.get("averagePackage")),
        clean(body.get("ownership")),
        clean(body.get("approval")),
        clean(body.get("exams")),
    )
    cursor.execute("SELECT 1 FROM engineering_facts WHERE college_slug = %s", (slug,))
    exists = cursor.fetchone() is not None
    if not exists and not any(value is not None and value != "" for value in values):
        return
    cursor.execute(
        """
        INSERT INTO engineering_facts (
            college_slug, source_slug, nirf_rank, fee_range, average_package, ownership, approval, exams
        ) VALUES (%s, 'admission-setu', %s, %s, %s, %s, %s, %s)
        ON CONFLICT (college_slug) DO UPDATE SET
            nirf_rank = EXCLUDED.nirf_rank,
            fee_range = EXCLUDED.fee_range,
            average_package = EXCLUDED.average_package,
            ownership = EXCLUDED.ownership,
            approval = EXCLUDED.approval,
            exams = EXCLUDED.exams
        """,
        (slug, *values),
    )


def _refresh_search(db, slug, previous=None):
    try:
        from api.search import COLLECTION, client
        from db.index_search import document
    except Exception:
        return "The college was saved. Search will update on the next index."
    try:
        typesense = client()
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT slug, name, city, state, type, category, rating, image_path,
                       priority, established, is_active
                FROM colleges WHERE slug = %s
                """,
                (slug,),
            )
            college = cursor.fetchone()
            cursor.execute(
                """
                SELECT course_name, course_group, specialization, fee_amount, fee_type
                FROM course_fees WHERE college_slug = %s
                """,
                (slug,),
            )
            fees = cursor.fetchall()
        for key in {previous, slug}:
            if not key:
                continue
            try:
                typesense.collections[COLLECTION].documents[key].delete()
            except Exception:
                pass
        if college and college["is_active"]:
            typesense.collections[COLLECTION].documents.upsert(document(college, fees))
    except Exception:
        return "The college was saved. Search will update on the next index."
    return ""


def _options(cursor):
    cursor.execute(
        """
        SELECT state FROM colleges
        WHERE state IS NOT NULL AND btrim(state) <> ''
        GROUP BY state ORDER BY state
        """
    )
    states = [row["state"] for row in cursor.fetchall()]
    cursor.execute(
        """
        SELECT category FROM colleges
        WHERE category IS NOT NULL AND btrim(category) <> ''
        GROUP BY category ORDER BY category
        """
    )
    categories = [row["category"] for row in cursor.fetchall()]
    return states, categories


@router.get("/status")
def status(db=Depends(connection)):
    total = staff_count(db)
    if total is None:
        return {"ready": False, "setup": False}
    return {"ready": True, "setup": total == 0}


@router.post("/setup")
def setup(body: dict, db=Depends(connection)):
    total = staff_count(db)
    if total is None:
        raise HTTPException(status_code=503, detail="Apply db/admin.sql before using the admin.")
    if total != 0:
        raise HTTPException(status_code=400, detail="An admin account already exists. Sign in.")
    try:
        email = _email(body.get("email"))
        name = clean(body.get("name"))
        password = _password(body.get("password"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not name:
        raise HTTPException(status_code=400, detail="Enter a name.")
    token = new_token()
    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO staff (email, name, password_hash, role)
            VALUES (%s, %s, %s, 'admin')
            RETURNING id, email, name, role
            """,
            (email, name, hash_password(password)),
        )
        staff = cursor.fetchone()
        cursor.execute(
            "INSERT INTO staff_sessions (token, staff_id, expires_at) VALUES (%s, %s, %s)",
            (token, staff["id"], expiry()),
        )
    db.commit()
    return {"token": token, "user": _public(staff)}


@router.post("/login")
def login(body: dict, db=Depends(connection)):
    if staff_count(db) is None:
        raise HTTPException(status_code=503, detail="Apply db/admin.sql before using the admin.")
    email = str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM staff WHERE email = %s", (email,))
        staff = cursor.fetchone()
        if staff is None or not staff["is_active"] or not check_password(password, staff["password_hash"]):
            raise HTTPException(status_code=401, detail="Email or password is wrong.")
        token = new_token()
        cursor.execute(
            "INSERT INTO staff_sessions (token, staff_id, expires_at) VALUES (%s, %s, %s)",
            (token, staff["id"], expiry()),
        )
    db.commit()
    return {"token": token, "user": _public(staff)}


@router.post("/logout")
def logout(authorization: str = Header(default=""), db=Depends(connection)):
    token = authorization.removeprefix("Bearer ").strip()
    if token and token != authorization:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM staff_sessions WHERE token = %s", (token,))
        db.commit()
    return {"ok": True}


@router.get("/me")
def me(staff=Depends(current_staff)):
    return _public(staff)


@router.get("/summary")
def summary(staff=Depends(current_staff), db=Depends(connection)):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*)::int AS colleges,
                COUNT(*) FILTER (WHERE is_active)::int AS active,
                COUNT(*) FILTER (WHERE NOT is_active)::int AS hidden
            FROM colleges
            """
        )
        counts = cursor.fetchone()
        cursor.execute("SELECT COUNT(*)::int AS total FROM engineering_facts WHERE nirf_rank IS NOT NULL")
        nirf = cursor.fetchone()["total"]
    payload = {**counts, "withNirf": nirf, "user": _public(staff)}
    if staff["role"] == "admin":
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*)::int AS total FROM staff WHERE is_active")
            payload["staff"] = cursor.fetchone()["total"]
    return payload


@router.get("/colleges")
def colleges(
    q: str = "",
    state: str = "",
    city: str = "",
    category: str = "",
    status: str = "all",
    sort: str = "name",
    page: int = 1,
    staff=Depends(current_staff),
    db=Depends(connection),
):
    del staff
    page = max(1, min(page, 2000))
    query = q.strip()[:80]
    where = ["1 = 1"]
    values = []
    if query:
        where.append("(c.name ILIKE %s OR c.slug ILIKE %s OR c.city ILIKE %s)")
        like = f"%{query}%"
        values.extend([like, like, like])
    if state.strip():
        where.append("c.state = %s")
        values.append(state.strip())
    if city.strip():
        where.append("c.city ILIKE %s")
        values.append(f"%{city.strip()}%")
    if category.strip():
        where.append("c.category = %s")
        values.append(category.strip())
    if status == "shown":
        where.append("c.is_active IS TRUE")
    elif status == "hidden":
        where.append("c.is_active IS FALSE")
    order = SORTS.get(sort, SORTS["name"])
    clause = " AND ".join(where)
    with db.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*)::int AS total FROM colleges c WHERE {clause}", values)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"""
            SELECT c.slug, c.name, c.city, c.state, c.category, c.type, c.is_active, c.priority, f.nirf_rank
            FROM colleges c
            LEFT JOIN engineering_facts f ON f.college_slug = c.slug
            WHERE {clause}
            ORDER BY {order}
            LIMIT %s OFFSET %s
            """,
            [*values, PAGE_SIZE, (page - 1) * PAGE_SIZE],
        )
        items = [
            {
                "slug": row["slug"],
                "name": row["name"],
                "city": row["city"],
                "state": row["state"],
                "category": row["category"],
                "type": row["type"],
                "active": row["is_active"],
                "priority": row["priority"],
                "nirf": row["nirf_rank"],
            }
            for row in cursor.fetchall()
        ]
        states, categories = _options(cursor)
    return {
        "total": total,
        "page": page,
        "pageSize": PAGE_SIZE,
        "q": query,
        "state": state.strip(),
        "city": city.strip(),
        "category": category.strip(),
        "status": status if status in {"shown", "hidden"} else "all",
        "sort": sort if sort in SORTS else "name",
        "states": states,
        "categories": categories,
        "items": items,
    }


@router.post("/colleges")
def create_college(body: dict, staff=Depends(current_staff), db=Depends(connection)):
    del staff
    name = clean(body.get("name"))
    try:
        slug = _slug(body.get("slug"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not name:
        raise HTTPException(status_code=400, detail="Enter a college name.")
    with db.cursor() as cursor:
        cursor.execute("SELECT 1 FROM colleges WHERE slug = %s", (slug,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="That slug is already used.")
        cursor.execute(
            "INSERT INTO colleges (slug, name, is_active) VALUES (%s, %s, true)",
            (slug, name),
        )
    db.commit()
    return {"slug": slug}


@router.get("/colleges/{slug}")
def read_college(slug: str, staff=Depends(current_staff), db=Depends(connection)):
    del staff
    with db.cursor() as cursor:
        row, facts = _load(cursor, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="College not found")
    return college_form(row, facts)


@router.patch("/colleges/{slug}")
def update_college(slug: str, body: dict, staff=Depends(current_staff), db=Depends(connection)):
    del staff
    name = clean(body.get("name"))
    if not name:
        raise HTTPException(status_code=400, detail="Enter a college name.")
    try:
        new_slug = _slug(body.get("slug") or slug)
        established = _whole(body.get("established"), "Established year")
        priority = _whole(body.get("priority"), "Priority")
        featured = _whole(body.get("featuredRank"), "Home order")
        reviews = _whole(body.get("reviews"), "Reviews")
        rating = _decimal(body.get("rating"), "Rating")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    active = bool(body.get("active"))
    lists = {}
    for key in ("approvals", "gallery", "tags"):
        items = _split(body.get(key))
        lists[key] = Jsonb(items) if items else None
    try:
        with db.transaction():
            with db.cursor() as cursor:
                cursor.execute("SELECT 1 FROM colleges WHERE slug = %s", (slug,))
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="College not found")
                target = slug
                if new_slug != slug:
                    _move_slug(cursor, slug, new_slug)
                    target = new_slug
                assignments = ["name = %s", "is_active = %s", "established = %s", "priority = %s", "featured_rank = %s", "rating = %s", "reviews = %s"]
                values = [name, active, established, priority, featured, rating, reviews]
                for key, column in TEXT.items():
                    assignments.append(f"{column} = %s")
                    values.append(clean(body.get(key)))
                for column, value in lists.items():
                    assignments.append(f"{column} = %s")
                    values.append(value)
                values.append(target)
                cursor.execute(
                    f"UPDATE colleges SET {', '.join(assignments)} WHERE slug = %s",
                    values,
                )
                _save_facts(cursor, target, body)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    notice = _refresh_search(db, new_slug, slug if new_slug != slug else None)
    return {"slug": new_slug, "notice": notice}


@router.get("/staff")
def list_staff(staff=Depends(require_admin), db=Depends(connection)):
    del staff
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, name, role, is_active, created_at
            FROM staff ORDER BY id
            """
        )
        rows = cursor.fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "active": row["is_active"],
                "created": row["created_at"].strftime("%d %b %Y"),
            }
            for row in rows
        ]
    }


@router.post("/staff")
def create_staff(body: dict, staff=Depends(require_admin), db=Depends(connection)):
    del staff
    try:
        email = _email(body.get("email"))
        password = _password(body.get("password"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    name = clean(body.get("name"))
    role = body.get("role") if body.get("role") in {"admin", "editor"} else ""
    if not name:
        raise HTTPException(status_code=400, detail="Enter a name.")
    if not role:
        raise HTTPException(status_code=400, detail="Choose Admin or Editor.")
    with db.cursor() as cursor:
        cursor.execute("SELECT 1 FROM staff WHERE email = %s", (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="That email is already used.")
        cursor.execute(
            """
            INSERT INTO staff (email, name, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (email, name, hash_password(password), role),
        )
    db.commit()
    return {"ok": True}


@router.patch("/staff/{staff_id}")
def update_staff(staff_id: int, body: dict, staff=Depends(require_admin), db=Depends(connection)):
    active = bool(body.get("active"))
    if staff["id"] == staff_id and not active:
        raise HTTPException(status_code=400, detail="You cannot turn off your own account.")
    with db.cursor() as cursor:
        cursor.execute("SELECT id, role, is_active FROM staff WHERE id = %s", (staff_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")
        if row["role"] == "admin" and row["is_active"] and not active:
            cursor.execute(
                "SELECT COUNT(*)::int AS total FROM staff WHERE role = 'admin' AND is_active AND id <> %s",
                (staff_id,),
            )
            if cursor.fetchone()["total"] == 0:
                raise HTTPException(status_code=400, detail="Keep at least one active admin.")
        cursor.execute("UPDATE staff SET is_active = %s WHERE id = %s", (active, staff_id))
        if not active:
            cursor.execute("DELETE FROM staff_sessions WHERE staff_id = %s", (staff_id,))
    db.commit()
    return {"ok": True}
