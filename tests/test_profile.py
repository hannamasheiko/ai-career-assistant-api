import uuid

import pytest


def create_test_user(client) -> dict:
    """Create and return a registered test user."""

    unique_suffix = uuid.uuid4().hex[:8]

    user_data = {
        "username": f"profile_user_{unique_suffix}",
        "email": f"profile_{unique_suffix}@example.com",
        "password": "TestPassword123!",
    }

    response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    return user_data


def get_auth_headers(client, user_data: dict) -> dict[str, str]:
    """Log in a test user and return authorization headers."""

    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def get_profile_payload(user_data: dict) -> dict:
    """Return valid candidate profile data."""

    return {
        "full_name": "Test Candidate",
        "email": user_data["email"],
        "phone": "+380501234567",
        "location": "Lviv, Ukraine",
        "github_url": "https://github.com/test-candidate",
        "linkedin_url": "https://linkedin.com/in/test-candidate",
        "preferred_employment_types": ["full-time"],
        "preferred_work_formats": ["remote"],
        "preferred_locations": ["Lviv", "Remote"],
        "willing_to_relocate": False,
        "desired_salary_min": 1000,
        "desired_roles": ["Python Backend Developer"],
    }


def create_test_profile(
    client,
    auth_headers: dict[str, str],
    user_data: dict,
) -> dict:
    """Create and return a candidate profile for test setup."""

    profile_data = get_profile_payload(user_data)

    response = client.post(
        "/profile",
        headers=auth_headers,
        json=profile_data,
    )

    assert response.status_code == 201

    return response.json()


def test_create_candidate_profile(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile_data = get_profile_payload(user_data)

    response = client.post(
        "/profile",
        headers=auth_headers,
        json=profile_data,
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["full_name"] == profile_data["full_name"]
    assert response_data["email"] == profile_data["email"]
    assert response_data["location"] == profile_data["location"]
    assert response_data["desired_salary_min"] == 1000
    assert response_data["desired_roles"] == [
        "Python Backend Developer"
    ]

    assert "id" in response_data
    assert "user_id" in response_data
    assert "created_at" in response_data
    assert "updated_at" in response_data


def test_get_current_user_profile(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)

    created_profile = create_test_profile(
        client=client,
        auth_headers=auth_headers,
        user_data=user_data,
    )

    response = client.get(
        "/profile/me",
        headers=auth_headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == created_profile["id"]
    assert response_data["user_id"] == created_profile["user_id"]
    assert response_data["full_name"] == created_profile["full_name"]
    assert response_data["email"] == created_profile["email"]


def test_update_current_user_profile(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)

    created_profile = create_test_profile(
        client=client,
        auth_headers=auth_headers,
        user_data=user_data,
    )

    update_data = {
        "location": "Kyiv, Ukraine",
        "desired_salary_min": 1500,
        "willing_to_relocate": True,
    }

    response = client.patch(
        "/profile/me",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["location"] == "Kyiv, Ukraine"
    assert response_data["desired_salary_min"] == 1500
    assert response_data["willing_to_relocate"] is True

    # Fields omitted from PATCH must remain unchanged.
    assert response_data["full_name"] == created_profile["full_name"]
    assert response_data["email"] == created_profile["email"]

    get_response = client.get(
        "/profile/me",
        headers=auth_headers,
    )

    assert get_response.status_code == 200

    saved_profile = get_response.json()

    assert saved_profile["location"] == "Kyiv, Ukraine"
    assert saved_profile["desired_salary_min"] == 1500
    assert saved_profile["willing_to_relocate"] is True


def test_cannot_create_second_candidate_profile(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile_data = get_profile_payload(user_data)

    first_response = client.post(
        "/profile",
        headers=auth_headers,
        json=profile_data,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/profile",
        headers=auth_headers,
        json=profile_data,
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Candidate profile already exists for this user"
    )


def test_get_profile_returns_404_when_profile_does_not_exist(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)

    response = client.get(
        "/profile/me",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate profile not found"


@pytest.mark.parametrize(
    ("method", "path", "json_data"),
    [
        (
            "post",
            "/profile",
            {
                "full_name": "Unauthorized Candidate",
                "email": "unauthorized@example.com",
            },
        ),
        ("get", "/profile/me", None),
        (
            "patch",
            "/profile/me",
            {
                "location": "Lviv, Ukraine",
            },
        ),
    ],
)
def test_profile_endpoints_require_authentication(
    client,
    method,
    path,
    json_data,
):
    response = client.request(
        method=method,
        url=path,
        json=json_data,
    )

    assert response.status_code == 401