import uuid
from datetime import datetime, timezone
from decimal import Decimal


VALID_RESUME_TEXT = (
    "Python Backend Developer with commercial experience in FastAPI, "
    "PostgreSQL, SQLAlchemy, REST API integrations and AI applications."
)


def create_test_user(client) -> dict:
    """Create and return a registered test user."""

    unique_suffix = uuid.uuid4().hex[:8]

    user_data = {
        "username": f"resume_user_{unique_suffix}",
        "email": f"resume_{unique_suffix}@example.com",
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


def create_test_profile(
    client,
    auth_headers: dict[str, str],
    user_data: dict,
) -> dict:
    """Create and return a candidate profile."""

    response = client.post(
        "/profile",
        headers=auth_headers,
        json={
            "full_name": "Resume Test Candidate",
            "email": user_data["email"],
        },
    )

    assert response.status_code == 201

    return response.json()


def build_mock_resume_result(
    candidate_profile_id: int,
    raw_text: str,
    file_name: str | None,
):
    """Build data matching ResumeIngestionResponse."""

    now = datetime.now(timezone.utc)

    resume_document = {
        "id": 1,
        "candidate_profile_id": candidate_profile_id,
        "file_name": file_name,
        "file_type": "text/plain",
        "source_type": "manual_text",
        "raw_text": raw_text,
        "is_active": True,
        "uploaded_at": now,
        "created_at": now,
        "updated_at": now,
    }

    resume_analysis = {
        "id": 1,
        "resume_document_id": 1,
        "full_name": "Resume Test Candidate",
        "target_role": "Python Backend Developer",
        "years_of_experience": Decimal("2.0"),
        "english_level": "B1",
        "location": "Lviv",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "summary": "Python backend developer.",
        "education_level": "Master",
        "education_summary": "Computer Science",
        "languages": ["Ukrainian", "English"],
        "ai_model": "gpt-5.4-mini",
        "prompt_version": "1.0",
        "created_at": now,
        "updated_at": now,
    }

    resume_sections = [
        {
            "id": 1,
            "resume_document_id": 1,
            "section_type": "summary",
            "title": "Summary",
            "content": "Python backend developer.",
            "order_index": 0,
        },
        {
            "id": 2,
            "resume_document_id": 1,
            "section_type": "skills",
            "title": "Skills",
            "content": "Python, FastAPI, PostgreSQL",
            "order_index": 1,
        },
    ]

    return resume_document, resume_analysis, resume_sections


def test_create_resume_from_text(client, monkeypatch):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile = create_test_profile(client, auth_headers, user_data)

    file_name = "python_backend_resume.txt"

    async def mock_create_resume_from_text(
        db,
        candidate_profile,
        raw_text,
        file_name,
    ):
        assert candidate_profile.id == profile["id"]
        assert raw_text == VALID_RESUME_TEXT
        assert file_name == "python_backend_resume.txt"

        return build_mock_resume_result(
            candidate_profile_id=candidate_profile.id,
            raw_text=raw_text,
            file_name=file_name,
        )

    monkeypatch.setattr(
        "app.api.resumes.create_resume_from_text",
        mock_create_resume_from_text,
    )

    response = client.post(
        "/resumes/from-text",
        params={"file_name": file_name},
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 201

    response_data = response.json()

    resume_document = response_data["resume_document"]
    resume_analysis = response_data["resume_analysis"]
    resume_sections = response_data["resume_sections"]

    assert resume_document["candidate_profile_id"] == profile["id"]
    assert resume_document["file_name"] == file_name
    assert resume_document["raw_text"] == VALID_RESUME_TEXT
    assert resume_document["source_type"] == "manual_text"
    assert resume_document["is_active"] is True

    assert resume_analysis["resume_document_id"] == resume_document["id"]
    assert resume_analysis["target_role"] == "Python Backend Developer"
    assert resume_analysis["skills"] == [
        "Python",
        "FastAPI",
        "PostgreSQL",
    ]

    assert len(resume_sections) == 2
    assert resume_sections[0]["section_type"] == "summary"
    assert resume_sections[1]["section_type"] == "skills"


def test_create_resume_without_file_name(client, monkeypatch):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile = create_test_profile(client, auth_headers, user_data)

    async def mock_create_resume_from_text(
        db,
        candidate_profile,
        raw_text,
        file_name,
    ):
        assert file_name is None

        return build_mock_resume_result(
            candidate_profile_id=profile["id"],
            raw_text=raw_text,
            file_name=file_name,
        )

    monkeypatch.setattr(
        "app.api.resumes.create_resume_from_text",
        mock_create_resume_from_text,
    )

    response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 201
    assert response.json()["resume_document"]["file_name"] is None


def test_create_resume_requires_authentication(client):
    response = client.post(
        "/resumes/from-text",
        headers={"Content-Type": "text/plain"},
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 401


def test_create_resume_requires_candidate_profile(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)

    response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Candidate profile not found. Create your profile first."
    )


def test_create_resume_rejects_too_short_text(client):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)

    response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content="Too short resume text.",
    )

    assert response.status_code == 422


def test_create_resume_returns_500_when_service_fails(
    client,
    monkeypatch,
):
    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)

    async def mock_create_resume_from_text(
        db,
        candidate_profile,
        raw_text,
        file_name,
    ):
        raise RuntimeError("OpenAI resume parsing failed")

    monkeypatch.setattr(
        "app.api.resumes.create_resume_from_text",
        mock_create_resume_from_text,
    )

    response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "OpenAI resume parsing failed"