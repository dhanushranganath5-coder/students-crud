# Students Database CRUD API

Python backend for managing student records: **FastAPI + SQLite**, with an **optional local Ollama** Q&A endpoint.
Built for the EWB Edu Tech Python Backend internship assignment.

## Features
- Create, Read (list, filter, single), Update (PUT & PATCH), Delete
- Persistent SQLite storage (`students.db`, created automatically)
- Validation (email, phone, DOB in the past, at least one contact) and clean 404 / 409 / 422 errors
- Interactive API docs at `/docs`
- Optional `POST /ask`: ask questions in plain English, answered by a local Ollama model using only retrieved records (the model never runs SQL)

## Prerequisites
- Python 3.10+
- (Optional) [Ollama](https://ollama.com) with `ollama pull llama3.2:1b`

## Installation
```bash
git clone https://github.com/<your-username>/students-crud.git
cd students-crud
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                   # optional: load 5 DUMMY students
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

## Tests
```bash
pytest -q
```

## Project structure
```
app/main.py       FastAPI routes
app/database.py   SQLite connection + schema
app/schemas.py    Pydantic models and validation
app/ai.py         Optional Ollama extension
seed.py           Dummy data loader
tests/            Automated API tests
```

## Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter (`name`, `course`, `email`, `born_after`, `born_before`, `skip`, `limit`) |
| GET | `/students/{id}` | View a student |
| PUT | `/students/{id}` | Replace all details |
| PATCH | `/students/{id}` | Update only the fields sent |
| DELETE | `/students/{id}` | Delete a student |
| POST | `/ask` | (Optional) Ask a question via Ollama |

## API testing (curl)
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Asha Kumar","date_of_birth":"2005-04-02","email":"asha@example.com","course":"Data Science"}'

# List / filter
curl "http://127.0.0.1:8000/students?course=Data%20Science&born_after=2004-12-31"

# View one
curl http://127.0.0.1:8000/students/1

# Update
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" -d '{"course":"Cyber Security"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1

# Ask (needs Ollama running)
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d '{"question":"List students born after 2005"}'
```

## Notes
- Only dummy data is used; `.db` files are git-ignored. No secrets are stored.
- If Ollama is not running, `/ask` still returns an answer built directly from the retrieved records.
- Config via env vars: `STUDENTS_DB`, `OLLAMA_URL`, `OLLAMA_MODEL`.
