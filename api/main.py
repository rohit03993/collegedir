from fastapi import Depends, FastAPI, HTTPException, Query

from api.admin import router as admin_router
from api.catalogue import apply_photos, college_payload, home_payload
from api.content import (
    article_detail,
    course_detail,
    exam_detail,
    list_articles,
    list_courses,
    list_exams,
    list_scholarships,
    scholarship_detail,
)
from api.db import connect
from api.images import serve_media
from api.predictor import form_options, prediction_payload, student_from_form
from api.search import SearchUnavailable, search_colleges

app = FastAPI(title="Admission Setu catalogue")
app.include_router(admin_router)


def connection():
    try:
        opened = connect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is not available. Check DATABASE_URL and that the new database is running.",
        ) from exc
    try:
        yield opened
    finally:
        opened.close()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/home")
def home(db=Depends(connection)):
    return home_payload(db)


@app.get("/api/predict")
def predict_rank(
    exam: str = "",
    rank: str = "",
    category: str = "",
    gender: str = "",
    home_state: str = "",
    crl: str = "",
    branch: str = "",
    page: int = Query(default=1, ge=1, le=2000),
    db=Depends(connection),
):
    if not any(value.strip() for value in (exam, rank, category, gender, home_state, crl)):
        return {"options": form_options(), "result": None}
    try:
        student = student_from_form(exam, rank, category, gender, home_state, crl)
    except ValueError as exc:
        return {"options": form_options(), "result": None, "error": str(exc)}
    try:
        result = prediction_payload(db, student, branch.strip(), page)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="The 2026 rank files are missing.") from exc
    return {"options": form_options(), "result": result}


@app.get("/api/colleges")
def colleges(
    q: str = "",
    state: list[str] = Query(default=[]),
    city: list[str] = Query(default=[]),
    course: list[str] = Query(default=[]),
    branch: list[str] = Query(default=[]),
    stream: list[str] = Query(default=[]),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=250),
    db=Depends(connection),
):
    try:
        result = search_colleges(q, state, city, course, branch, stream, page, per_page)
    except SearchUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    apply_photos(db, result["colleges"])
    return result


@app.get("/api/exams")
def exams(q: str = "", category: str = "", page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=400), db=Depends(connection)):
    return list_exams(db, q, category, page, per_page)


@app.get("/api/exams/{slug}")
def exam(slug: str, db=Depends(connection)):
    payload = exam_detail(db, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return payload


@app.get("/api/courses")
def courses(q: str = "", category: str = "", page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=400), db=Depends(connection)):
    return list_courses(db, q, category, page, per_page)


@app.get("/api/courses/{slug}")
def course(slug: str, db=Depends(connection)):
    payload = course_detail(db, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return payload


@app.get("/api/articles")
def articles(q: str = "", page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=400), db=Depends(connection)):
    return list_articles(db, q, page, per_page)


@app.get("/api/articles/{slug}")
def article(slug: str, db=Depends(connection)):
    payload = article_detail(db, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return payload


@app.get("/api/scholarships")
def scholarships(q: str = "", page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=400), db=Depends(connection)):
    return list_scholarships(db, q, page, per_page)


@app.get("/api/scholarships/{slug}")
def scholarship(slug: str, db=Depends(connection)):
    payload = scholarship_detail(db, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    return payload


@app.get("/media/{file_path:path}")
def media(file_path: str, db=Depends(connection)):
    return serve_media(db, file_path)


@app.get("/api/colleges/{slug}")
def college(slug: str, db=Depends(connection)):
    payload = college_payload(db, slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="College not found")
    return payload
