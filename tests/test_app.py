
import pytest

from app import create_app
from extensions import db


@pytest.fixture
def app(tmp_path):
    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })

    with test_app.app_context():
        db.create_all()

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, username="caleb", password="TestPass123!"):
    return client.post("/signup", json={
        "username": username,
        "password": password,
        "password_confirmation": password,
    })


def login(client, username="caleb", password="TestPass123!"):
    return client.post("/login", json={
        "username": username,
        "password": password,
    })


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["message"] == "Flask backend is running"


def test_signup_creates_user_and_starts_session(client):
    response = signup(client)

    assert response.status_code == 201
    assert response.json["username"] == "caleb"
    assert "password_hash" not in response.json

    session_response = client.get("/check_session")
    assert session_response.status_code == 200
    assert session_response.json["username"] == "caleb"


def test_signup_rejects_duplicate_username(client):
    signup(client)
    response = signup(client)
    assert response.status_code == 409


def test_signup_rejects_password_mismatch(client):
    response = client.post("/signup", json={
        "username": "another_user",
        "password": "TestPass123!",
        "password_confirmation": "DifferentPass123!",
    })
    assert response.status_code == 400


def test_login_with_correct_credentials(client):
    signup(client)
    client.delete("/logout")

    response = login(client)

    assert response.status_code == 200
    assert response.json["username"] == "caleb"


def test_login_rejects_wrong_password(client):
    signup(client)
    client.delete("/logout")

    response = login(client, password="WrongPassword123!")
    assert response.status_code == 401


def test_logout_clears_session(client):
    signup(client)

    logout_response = client.delete("/logout")
    session_response = client.get("/check_session")

    assert logout_response.status_code == 200
    assert logout_response.json == {}
    assert session_response.json == {}


def test_notes_require_authentication(client):
    response = client.get("/notes")
    assert response.status_code == 401


def test_user_can_create_read_update_and_delete_note(client):
    signup(client)

    create_response = client.post("/notes", json={
        "title": "First note",
        "content": "Testing CRUD operations",
    })

    assert create_response.status_code == 201
    note_id = create_response.json["id"]

    read_response = client.get(f"/notes/{note_id}")
    assert read_response.status_code == 200
    assert read_response.json["title"] == "First note"

    update_response = client.patch(f"/notes/{note_id}", json={
        "title": "Updated note",
    })

    assert update_response.status_code == 200
    assert update_response.json["title"] == "Updated note"
    assert update_response.json["content"] == "Testing CRUD operations"

    delete_response = client.delete(f"/notes/{note_id}")
    assert delete_response.status_code == 200
    assert delete_response.json == {}

    missing_response = client.get(f"/notes/{note_id}")
    assert missing_response.status_code == 404


def test_users_cannot_access_another_users_notes(client):
    signup(client, username="user_one")

    note_response = client.post("/notes", json={
        "title": "Private note",
        "content": "Only user one should access this",
    })

    note_id = note_response.json["id"]

    client.delete("/logout")
    signup(client, username="user_two")

    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 404


def test_notes_pagination(client):
    signup(client)

    for number in range(3):
        response = client.post("/notes", json={
            "title": f"Note {number + 1}",
            "content": "Pagination test",
        })
        assert response.status_code == 201

    response = client.get("/notes?page=1&per_page=2")

    assert response.status_code == 200
    assert len(response.json["notes"]) == 2
    assert response.json["page"] == 1
    assert response.json["per_page"] == 2
    assert response.json["total"] == 3
    assert response.json["pages"] == 2
