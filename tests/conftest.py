"""Shared API test fixtures."""

import pytest

from app import create_app
from app.blueprints.auth.models import AdminUser
from app.commands import seed_database
from app.common.extensions import db


@pytest.fixture()
def app(monkeypatch):
    """Create an isolated in-memory application."""
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "Admin@123456")
    application = create_app(
        "development",
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-jwt-secret-at-least-32-bytes-long",
            "SECRET_KEY": "test-app-secret",
        },
    )
    with application.app_context():
        db.create_all()
        seed_database()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Log in and return a bearer authorization header."""
    response = client.post(
        "/api/auth/login",
        json={"account": "admin", "password": "Admin@123456"},
    )
    token = response.get_json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_id(app):
    """Return the seeded administrator identifier."""
    with app.app_context():
        return db.session.scalar(
            db.select(AdminUser.id).where(AdminUser.account == "admin")
        )
