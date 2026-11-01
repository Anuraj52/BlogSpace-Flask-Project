import pytest
from app import create_app, db, User, Post

@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def register_and_login(client):
    client.post("/register", data={
        "username": "tester",
        "email": "tester@example.com",
        "password": "strongpass123",
        "confirm_password": "strongpass123",
    }, follow_redirects=True)

def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Explore posts" in response.data

def test_register_and_login(client, app):
    register_and_login(client)
    with app.app_context():
        assert User.query.filter_by(email="tester@example.com").first() is not None
    client.post("/logout", follow_redirects=True)
    response = client.post("/login", data={
        "email": "tester@example.com",
        "password": "strongpass123",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back" in response.data

def test_create_post(client, app):
    register_and_login(client)
    response = client.post("/post/new", data={
        "title": "My first test post",
        "category": "Technology",
        "content": "This is a long enough test post body.",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert Post.query.filter_by(title="My first test post").first() is not None
