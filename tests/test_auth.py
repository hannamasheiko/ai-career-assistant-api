import uuid


def create_test_user(client):
    """
    Create a unique test user through the registration endpoint.

    This helper prepares a user for tests that require
    an existing registered user.
    """
    unique_suffix = uuid.uuid4().hex[:8]

    user_data = {
        "username": f"testuser_{unique_suffix}",
        "email": f"test_{unique_suffix}@example.com",
        "password": "TestPassword123!",
    }

    response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    return user_data


def login_test_user(client, user_data):
    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert "access_token" in response_data
    assert response_data["access_token"]
    assert response_data["token_type"] == "bearer"

    return response_data["access_token"]

def test_register_user(client):
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
    }

    response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["username"] == user_data["username"]
    assert response_data["email"] == user_data["email"]
    assert "id" in response_data
    assert "password" not in response_data
    assert "hashed_password" not in response_data


def test_login_user(client):
    user_data = create_test_user(client)

    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert "access_token" in response_data
    assert response_data["access_token"]
    assert response_data["token_type"] == "bearer"


def test_login_with_invalid_credentials(client):
    user_data = create_test_user(client)

    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    response_data = response.json()

    assert "detail" in response_data


def test_get_current_user(client):
    user_data = create_test_user(client)
    access_token = login_test_user(client, user_data)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["username"] == user_data["username"]
    assert response_data["email"] == user_data["email"]
    assert "id" in response_data
    assert "password" not in response_data
    assert "hashed_password" not in response_data

