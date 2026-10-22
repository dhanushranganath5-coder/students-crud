"""Load DUMMY sample data (no real personal information)."""
from app.database import get_conn, init_db

SAMPLE = [
    ("Aarav Sharma", "2004-03-12", "aarav@example.com", "9000000001", "Computer Science", "Bangalore", "2023-08-01"),
    ("Diya Patel", "2005-07-25", "diya@example.com", "9000000002", "Data Science", "Mysuru", "2024-08-01"),
    ("Kabir Rao", "2006-01-09", "kabir@example.com", None, "Computer Science", "Hubli", "2024-08-01"),
    ("Meera Nair", "2003-11-30", "meera@example.com", "9000000004", "Cyber Security", "Mangaluru", "2022-08-01"),
    ("Rohan Gupta", "2005-05-18", None, "9000000005", "Data Science", "Bangalore", "2023-08-01"),
]

if __name__ == "__main__":
    init_db()
    with get_conn() as conn:
        for row in SAMPLE:
            conn.execute(
                "INSERT OR IGNORE INTO students (name, date_of_birth, email, phone, course, address, enrollment_date) "
                "VALUES (?,?,?,?,?,?,?)", row)
    print(f"Seeded {len(SAMPLE)} dummy students.")
