from backend.app import create_app


def test_health_without_database():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLITE_PATH": ":memory:",
    })
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_login_without_database_returns_clear_error():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLITE_PATH": ":memory:",
    })
    response = app.test_client().post("/api/auth/login", json={"email": "x@example.com", "password": "abc"})
    assert response.status_code == 503
