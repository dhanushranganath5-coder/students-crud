"""Optional Ollama extension.

Safety design: the model NEVER writes or runs SQL. The backend maps the question
to a small set of fixed, parameterised queries, retrieves rows, and passes only
those rows to the model as context. If Ollama is not running, a deterministic
answer built from the same rows is returned.
"""
import json
import os
import re
import urllib.error
import urllib.request

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MAX_ROWS = 50


def retrieve(conn, question: str):
    """Return (rows, description, total_count) using fixed parameterised queries only."""
    q = question.lower()
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]

    m = re.search(r"born\s+(after|before|in)\s+(\d{4})", q)
    if m:
        kind, year = m.group(1), int(m.group(2))
        if kind == "after":
            where, p = "date_of_birth >= ?", (f"{year + 1}-01-01",)
        elif kind == "before":
            where, p = "date_of_birth < ?", (f"{year}-01-01",)
        else:
            where, p = "date_of_birth >= ? AND date_of_birth < ?", (f"{year}-01-01", f"{year + 1}-01-01")
        rows = conn.execute(f"SELECT * FROM students WHERE {where} ORDER BY date_of_birth LIMIT ?", (*p, MAX_ROWS)).fetchall()
        return rows, f"students born {kind} {year}", total

    courses = [r[0] for r in conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL")]
    for c in courses:
        if c.lower() in q:
            rows = conn.execute("SELECT * FROM students WHERE LOWER(course) = LOWER(?) LIMIT ?", (c, MAX_ROWS)).fetchall()
            return rows, f"students in course {c}", total

    for r in conn.execute("SELECT * FROM students").fetchall():
        if r["name"].lower() in q:
            return [r], f"student named {r['name']}", total

    rows = conn.execute("SELECT * FROM students ORDER BY id LIMIT ?", (MAX_ROWS,)).fetchall()
    return rows, "all students (first %d)" % MAX_ROWS, total


def _fallback(question, rows, desc, total):
    if re.search(r"how many|count|number of", question.lower()) and desc.startswith("all"):
        return f"There are {total} students in the database."
    names = ", ".join(f"{r['name']} (DOB {r['date_of_birth']})" for r in rows) or "none"
    return f"Found {len(rows)} record(s) for {desc}: {names}."


def answer_question(conn, question: str):
    rows, desc, total = retrieve(conn, question)
    context = "\n".join(
        f"- id={r['id']}, name={r['name']}, dob={r['date_of_birth']}, course={r['course']}" for r in rows
    )
    prompt = (
        "You answer questions about a student database. Use ONLY the data below. "
        "If the answer is not in the data, say you don't know.\n\n"
        f"Total students in database: {total}\n"
        f"Retrieved records ({desc}), {len(rows)} row(s):\n{context or '(none)'}\n\n"
        f"Question: {question}\nAnswer briefly:"
    )
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = json.loads(resp.read())["response"].strip()
            if text:
                return text, len(rows)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        pass
    return _fallback(question, rows, desc, total) + " (Ollama unavailable; answered without the model.)", len(rows)
