import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status

from . import ai
from .database import get_conn, init_db
from .schemas import (AskRequest, AskResponse, StudentCreate, StudentOut,
                      StudentUpdate)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Students Database CRUD API",
    description="FastAPI + SQLite student records, with an optional local Ollama Q&A endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)

COLUMNS = ("name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date")


def row_to_student(row: sqlite3.Row) -> dict:
    return dict(row)


def to_db(data: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items()}


def fetch_or_404(conn, student_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    return row


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "docs": "/docs"}


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED, tags=["students"])
def create_student(student: StudentCreate):
    data = to_db(student.model_dump())
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO students ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                tuple(data[c] for c in COLUMNS),
            )
            row = fetch_or_404(conn, cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")
    return row_to_student(row)


@app.get("/students", response_model=List[StudentOut], tags=["students"])
def list_students(
    name: Optional[str] = Query(None, description="Partial, case-insensitive name match"),
    course: Optional[str] = Query(None, description="Exact course (case-insensitive)"),
    email: Optional[str] = None,
    born_after: Optional[date] = Query(None, description="DOB strictly after this date"),
    born_before: Optional[date] = Query(None, description="DOB strictly before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    sql, params = "SELECT * FROM students WHERE 1=1", []
    if name:
        sql += " AND name LIKE ?"
        params.append(f"%{name}%")
    if course:
        sql += " AND LOWER(course) = LOWER(?)"
        params.append(course)
    if email:
        sql += " AND email = ?"
        params.append(email.strip().lower())
    if born_after:
        sql += " AND date_of_birth > ?"
        params.append(born_after.isoformat())
    if born_before:
        sql += " AND date_of_birth < ?"
        params.append(born_before.isoformat())
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, skip]
    with get_conn() as conn:
        return [row_to_student(r) for r in conn.execute(sql, params).fetchall()]


@app.get("/students/{student_id}", response_model=StudentOut, tags=["students"])
def get_student(student_id: int):
    with get_conn() as conn:
        return row_to_student(fetch_or_404(conn, student_id))


@app.put("/students/{student_id}", response_model=StudentOut, tags=["students"])
def replace_student(student_id: int, student: StudentCreate):
    """Full update: every field is replaced."""
    data = to_db(student.model_dump())
    try:
        with get_conn() as conn:
            fetch_or_404(conn, student_id)
            conn.execute(
                f"UPDATE students SET {', '.join(c + ' = ?' for c in COLUMNS)} WHERE id = ?",
                (*[data[c] for c in COLUMNS], student_id),
            )
            row = fetch_or_404(conn, student_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")
    return row_to_student(row)


@app.patch("/students/{student_id}", response_model=StudentOut, tags=["students"])
def update_student(student_id: int, changes: StudentUpdate):
    """Partial update: only the fields sent are changed."""
    data = to_db(changes.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=422, detail="No fields provided to update")
    for required in ("name", "date_of_birth"):
        if required in data and data[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} cannot be null")
    try:
        with get_conn() as conn:
            fetch_or_404(conn, student_id)
            conn.execute(
                f"UPDATE students SET {', '.join(k + ' = ?' for k in data)} WHERE id = ?",
                (*data.values(), student_id),
            )
            row = fetch_or_404(conn, student_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")
    if not row["email"] and not row["phone"]:
        raise HTTPException(status_code=422, detail="Student must keep at least one of email or phone")
    return row_to_student(row)


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["students"])
def delete_student(student_id: int):
    with get_conn() as conn:
        fetch_or_404(conn, student_id)
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/ask", response_model=AskResponse, tags=["ai (optional)"])
def ask(req: AskRequest):
    """Natural-language questions answered by a local Ollama model from retrieved records."""
    with get_conn() as conn:
        answer, used = ai.answer_question(conn, req.question)
    return AskResponse(question=req.question, answer=answer, records_used=used)
