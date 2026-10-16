import sqlite3
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    return connection


def initialize(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS report_users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS report_internships (
                internship_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS report_applications (
                application_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                internship_id TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES report_users(user_id),
                FOREIGN KEY(internship_id) REFERENCES report_internships(internship_id)
            );
            '''
        )


def upsert_user(db_path: str, user_id: str, display_name: str, role: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            '''INSERT INTO report_users(user_id, display_name, role)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               display_name=excluded.display_name, role=excluded.role''',
            (user_id, display_name, role),
        )


def upsert_internship(db_path: str, internship_id: str, title: str, company_name: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            '''INSERT INTO report_internships(internship_id, title, company_name)
               VALUES (?, ?, ?)
               ON CONFLICT(internship_id) DO UPDATE SET
               title=excluded.title, company_name=excluded.company_name''',
            (internship_id, title, company_name),
        )


def upsert_application(db_path: str, application_id: str, user_id: str, internship_id: str, status: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            '''INSERT INTO report_applications(application_id, user_id, internship_id, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(application_id) DO UPDATE SET status=excluded.status''',
            (application_id, user_id, internship_id, status),
        )


def application_summary(db_path: str) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            '''
            SELECT i.title, i.company_name, a.status, COUNT(*) AS total
            FROM report_applications a
            JOIN report_internships i ON i.internship_id = a.internship_id
            GROUP BY i.internship_id, a.status
            ORDER BY i.title, total DESC
            '''
        ).fetchall()
    return [dict(row) for row in rows]
