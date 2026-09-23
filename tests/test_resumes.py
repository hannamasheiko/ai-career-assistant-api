from datetime import datetime, timezone
from decimal import Decimal
from app.core.exceptions import AIServiceError
from app.schemas.ai_outputs import (
    ParsedResume,
    ParsedResumeAnalysis,
    ParsedResumeSection,
)
from fastapi import status

from tests.conftest import create_test_user, get_auth_headers


VALID_RESUME_TEXT = (
    "Python Backend Developer with commercial experience in FastAPI, "
    "PostgreSQL, SQLAlchemy, REST API integrations and AI applications."
)


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


def mock_resume_parser(monkeypatch) -> None:
    """Mock AI resume parsing with deterministic structured data."""

    async def mock_parse_resume_chain(raw_text: str):
        return ParsedResume(
            resume_analysis=ParsedResumeAnalysis(
                full_name="Resume Test Candidate",
                target_role="Python Backend Developer",
                skills=["Python", "FastAPI", "PostgreSQL"],
                summary="Python backend developer.",
            ),
            sections=[
                ParsedResumeSection(
                    section_type="summary",
                    title="Summary",
                    content="Python backend developer.",
                    order_index=0,
                ),
                ParsedResumeSection(
                    section_type="skills",
                    title="Skills",
                    content="Python, FastAPI, PostgreSQL",
                    order_index=1,
                ),
            ],
        )

    monkeypatch.setattr(
        "app.services.resume_service.parse_resume_chain",
        mock_parse_resume_chain,
    )


def create_test_resume(
    client,
    auth_headers: dict[str, str],
    monkeypatch,
    *,
    file_name: str | None = None,
) -> dict:
    """Create and return a persisted resume document with mocked AI parsing."""

    mock_resume_parser(monkeypatch)

    response = client.post(
        "/resumes/from-text",
        params={"file_name": file_name} if file_name else {},
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 201

    return response.json()["resume_document"]


def test_create_resume_from_text(client, monkeypatch):
    user_data = create_test_user(client, prefix="resume")
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
    user_data = create_test_user(client, prefix="resume")
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
    user_data = create_test_user(client, prefix="resume")
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
    user_data = create_test_user(client, prefix="resume")
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


def test_create_resume_returns_503_when_ai_service_fails(
    client,
    monkeypatch,
):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)

    async def mock_create_resume_from_text(
        db,
        candidate_profile,
        raw_text,
        file_name,
    ):
        raise AIServiceError("OpenAI resume parsing failed")

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

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "detail": "AI service is temporarily unavailable. Please try again later."
    }


def test_get_resume_documents_returns_own_resumes(client, monkeypatch):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)

    first_resume = create_test_resume(
        client, auth_headers, monkeypatch, file_name="first.txt"
    )
    second_resume = create_test_resume(
        client, auth_headers, monkeypatch, file_name="second.txt"
    )

    response = client.get("/resumes", headers=auth_headers)

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 2
    assert {resume["id"] for resume in response_data} == {
        first_resume["id"],
        second_resume["id"],
    }
    # Newest resume document comes first.
    assert response_data[0]["id"] == second_resume["id"]
    assert response_data[1]["id"] == first_resume["id"]


def test_get_resume_documents_requires_authentication(client):
    response = client.get("/resumes")

    assert response.status_code == 401


def test_get_resume_documents_excludes_other_users_resumes(
    client,
    monkeypatch,
):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)
    create_test_resume(client, auth_headers, monkeypatch)

    other_user = create_test_user(client, prefix="resume")
    other_auth_headers = get_auth_headers(client, other_user)
    create_test_profile(client, other_auth_headers, other_user)

    response = client.get("/resumes", headers=other_auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_get_resume_document_by_id(client, monkeypatch):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)
    created_resume = create_test_resume(
        client, auth_headers, monkeypatch, file_name="my_resume.txt"
    )

    response = client.get(
        f"/resumes/{created_resume['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["resume_document"]["id"] == created_resume["id"]
    assert response_data["resume_document"]["file_name"] == "my_resume.txt"
    assert response_data["resume_analysis"]["resume_document_id"] == (
        created_resume["id"]
    )
    assert response_data["resume_analysis"]["target_role"] == (
        "Python Backend Developer"
    )
    assert [
        section["order_index"]
        for section in response_data["resume_sections"]
    ] == [0, 1]


def test_get_resume_document_requires_authentication(client):
    response = client.get("/resumes/1")

    assert response.status_code == 401


def test_get_nonexistent_resume_document_returns_404(client):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)

    response = client.get("/resumes/999999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume document not found."


def test_get_resume_document_returns_404_for_other_users_resume(
    client,
    monkeypatch,
):
    owner_data = create_test_user(client, prefix="resume")
    owner_auth_headers = get_auth_headers(client, owner_data)
    create_test_profile(client, owner_auth_headers, owner_data)
    created_resume = create_test_resume(
        client, owner_auth_headers, monkeypatch
    )

    other_user = create_test_user(client, prefix="resume")
    other_auth_headers = get_auth_headers(client, other_user)

    response = client.get(
        f"/resumes/{created_resume['id']}",
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume document not found."


def test_archive_resume_document(client, monkeypatch):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)
    created_resume = create_test_resume(client, auth_headers, monkeypatch)

    assert created_resume["is_active"] is True

    response = client.patch(
        f"/resumes/{created_resume['id']}",
        headers=auth_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    get_response = client.get(
        f"/resumes/{created_resume['id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["resume_document"]["is_active"] is False


def test_unarchive_resume_document(client, monkeypatch):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)
    created_resume = create_test_resume(client, auth_headers, monkeypatch)

    archive_response = client.patch(
        f"/resumes/{created_resume['id']}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["is_active"] is False

    unarchive_response = client.patch(
        f"/resumes/{created_resume['id']}",
        headers=auth_headers,
        json={"is_active": True},
    )

    assert unarchive_response.status_code == 200
    assert unarchive_response.json()["is_active"] is True


def test_update_resume_document_requires_authentication(client):
    response = client.patch(
        "/resumes/1",
        json={"is_active": False},
    )

    assert response.status_code == 401


def test_update_nonexistent_resume_document_returns_404(client):
    user_data = create_test_user(client, prefix="resume")
    auth_headers = get_auth_headers(client, user_data)

    response = client.patch(
        "/resumes/999999",
        headers=auth_headers,
        json={"is_active": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume document not found."


def test_update_resume_document_returns_404_for_other_users_resume(
    client,
    monkeypatch,
):
    owner_data = create_test_user(client, prefix="resume")
    owner_auth_headers = get_auth_headers(client, owner_data)
    create_test_profile(client, owner_auth_headers, owner_data)
    created_resume = create_test_resume(
        client, owner_auth_headers, monkeypatch
    )

    other_user = create_test_user(client, prefix="resume")
    other_auth_headers = get_auth_headers(client, other_user)

    response = client.patch(
        f"/resumes/{created_resume['id']}",
        headers=other_auth_headers,
        json={"is_active": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume document not found."