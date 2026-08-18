import uuid
from datetime import datetime

from app.schemas.ai_outputs import (
    ParsedResume,
    ParsedResumeAnalysis,
    ParsedResumeSection,
    ParsedVacancyDetails,
)


VALID_RESUME_TEXT = (
    "Python Backend Developer with commercial experience in FastAPI, "
    "PostgreSQL, SQLAlchemy, REST API integrations and AI applications."
)

VALID_VACANCY_TEXT = (
    "Python Backend Developer vacancy requiring FastAPI, PostgreSQL, "
    "SQLAlchemy, REST API experience and strong English skills."
)


def create_test_user(client) -> dict:
    """Create and return a registered test user."""

    unique_suffix = uuid.uuid4().hex[:8]
    user_data = {
        "username": f"interaction_user_{unique_suffix}",
        "email": f"interaction_{unique_suffix}@example.com",
        "password": "TestPassword123!",
    }

    response = client.post("/auth/register", json=user_data)

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

    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


def create_test_profile(client, auth_headers, user_data) -> None:
    """Create a candidate profile for a test user."""

    response = client.post(
        "/profile",
        headers=auth_headers,
        json={
            "full_name": "Interaction Test Candidate",
            "email": user_data["email"],
        },
    )

    assert response.status_code == 201


def mock_resume_parser(monkeypatch) -> None:
    """Mock AI resume parsing with deterministic structured data."""

    async def mock_parse_resume_chain(raw_text: str):
        assert raw_text == VALID_RESUME_TEXT

        return ParsedResume(
            resume_analysis=ParsedResumeAnalysis(
                full_name="Interaction Test Candidate",
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
            ],
        )

    monkeypatch.setattr(
        "app.services.resume_service.parse_resume_chain",
        mock_parse_resume_chain,
    )


def mock_vacancy_parser(monkeypatch) -> None:
    """Mock AI vacancy parsing with deterministic structured data."""

    async def mock_parse_vacancy_chain(raw_text: str):
        assert raw_text == VALID_VACANCY_TEXT

        return ParsedVacancyDetails(
            company_name="Test Company",
            position_title="Python Backend Developer",
            source="company_site",
            source_url="https://example.com/jobs/python-backend",
            location="Kyiv",
            work_format="remote",
            employment_type="full-time",
            cleaned_text=VALID_VACANCY_TEXT,
        )

    monkeypatch.setattr(
        "app.services.vacancy_service.parse_vacancy_chain",
        mock_parse_vacancy_chain,
    )


def prepare_interaction_data(client, monkeypatch) -> tuple[dict, dict]:
    """Create an authenticated user and a tracked vacancy."""

    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)

    mock_resume_parser(monkeypatch)
    resume_response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )
    assert resume_response.status_code == 201
    resume = resume_response.json()["resume_document"]

    mock_vacancy_parser(monkeypatch)
    vacancy_response = client.post(
        "/vacancies/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_VACANCY_TEXT,
    )
    assert vacancy_response.status_code == 201
    vacancy = vacancy_response.json()["vacancy"]

    tracked_response = client.post(
        "/tracked-vacancies",
        headers=auth_headers,
        json={
            "resume_document_id": resume["id"],
            "vacancy_id": vacancy["id"],
        },
    )
    assert tracked_response.status_code == 201

    return auth_headers, tracked_response.json()


def create_test_interaction(
    client,
    auth_headers: dict[str, str],
    tracked_vacancy_id: int,
    *,
    occurred_at: str = "2026-08-18T09:30:00+00:00",
    summary: str = "Sent an introductory message.",
) -> dict:
    """Create and return an interaction."""

    response = client.post(
        f"/tracked-vacancies/{tracked_vacancy_id}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "message",
            "direction": "outgoing",
            "message_text": "Hello, I am interested in this role.",
            "summary": summary,
            "occurred_at": occurred_at,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_interaction_updates_last_contact_at(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    occurred_at = "2026-08-18T09:30:00+00:00"

    response = client.post(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "message",
            "direction": "outgoing",
            "message_text": "Hello, I am interested in this role.",
            "summary": "Sent an introductory message.",
            "occurred_at": occurred_at,
        },
    )

    assert response.status_code == 201

    interaction = response.json()
    assert interaction["tracked_vacancy_id"] == tracked_vacancy["id"]
    assert interaction["interaction_type"] == "message"
    assert interaction["direction"] == "outgoing"
    assert interaction["message_text"] == (
        "Hello, I am interested in this role."
    )
    assert interaction["summary"] == "Sent an introductory message."
    assert interaction["id"] is not None
    assert interaction["created_at"] is not None
    assert interaction["updated_at"] is not None

    tracked_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert datetime.fromisoformat(
        tracked_response.json()["last_contact_at"],
    ) == datetime.fromisoformat(occurred_at)


def test_create_interaction_requires_authentication(client):
    response = client.post(
        "/tracked-vacancies/1/interactions",
        data={
            "interaction_type": "message",
            "direction": "outgoing",
        },
    )

    assert response.status_code == 401


def test_get_interactions_for_tracked_vacancy(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    older_interaction = create_test_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at="2026-08-17T09:30:00+00:00",
        summary="Older interaction.",
    )
    newer_interaction = create_test_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at="2026-08-18T09:30:00+00:00",
        summary="Newer interaction.",
    )

    response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        newer_interaction["id"],
        older_interaction["id"],
    ]
    assert all(
        item["tracked_vacancy_id"] == tracked_vacancy["id"]
        for item in response.json()
    )


def test_get_interaction_by_id(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    interaction = create_test_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
    )

    response = client.get(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
    )
    missing_response = client.get(
        "/tracked-vacancies/interactions/999999999",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == interaction
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Interaction not found."


def test_update_interaction(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    interaction = create_test_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
    )
    update_data = {
        "interaction_type": "call",
        "direction": "incoming",
        "message_text": "Recruiter called to discuss the position.",
        "summary": "Introductory recruiter call.",
    }

    response = client.patch(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200
    assert response.json()["interaction_type"] == "call"
    assert response.json()["direction"] == "incoming"
    assert response.json()["message_text"] == update_data["message_text"]
    assert response.json()["summary"] == update_data["summary"]

    get_response = client.get(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["interaction_type"] == "call"
    assert get_response.json()["summary"] == update_data["summary"]


def test_other_user_cannot_access_interactions(client, monkeypatch):
    owner_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    interaction = create_test_interaction(
        client,
        owner_headers,
        tracked_vacancy["id"],
    )
    other_user = create_test_user(client)
    other_user_headers = get_auth_headers(client, other_user)

    create_response = client.post(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=other_user_headers,
        data={
            "interaction_type": "call",
            "direction": "incoming",
        },
    )
    list_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=other_user_headers,
    )
    get_response = client.get(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=other_user_headers,
    )
    update_response = client.patch(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=other_user_headers,
        json={"summary": "Unauthorized update."},
    )

    assert create_response.status_code == 404
    assert create_response.json()["detail"] == "Tracked vacancy not found."
    assert list_response.status_code == 404
    assert list_response.json()["detail"] == "Tracked vacancy not found."
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Interaction not found."
    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Interaction not found."
