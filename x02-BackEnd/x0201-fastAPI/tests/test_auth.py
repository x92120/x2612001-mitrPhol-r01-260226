import pytest

def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "username": "testuser123",
            "email": "testuser123@example.com",
            "password": "testpass123",
            "full_name": "Test User",
            "role": "Operator",
            "department": "Production"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser123"
    assert "password" not in data  # Password should not be returned

def test_get_users(client):
    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_login(client):
    # First create a user
    client.post(
        "/users/",
        json={
            "username": "logintest",
            "email": "logintest@example.com",
            "password": "testpass123",
            "full_name": "Login Test",
            "role": "Operator"
        }
    )
    
    # Then try to login
    response = client.post(
        "/auth/login",
        data={
            "username": "logintest",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
