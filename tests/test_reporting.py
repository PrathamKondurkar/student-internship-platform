from backend.services.sqlite_reporting import (
    initialize, upsert_user, upsert_internship, upsert_application, application_summary
)


def test_sql_reporting_join_and_grouping(tmp_path):
    db_path = str(tmp_path / "report.db")
    initialize(db_path)
    upsert_user(db_path, "u1", "Student One", "student")
    upsert_internship(db_path, "i1", "Python Intern", "Example Co")
    upsert_application(db_path, "a1", "u1", "i1", "pending")
    upsert_application(db_path, "a2", "u1", "i1", "shortlisted")
    summary = application_summary(db_path)
    assert len(summary) == 2
    assert {row["status"] for row in summary} == {"pending", "shortlisted"}
