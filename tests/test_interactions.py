from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_outputs import (
    ParsedResume,
    ParsedResumeAnalysis,
    ParsedResumeSection,
    ParsedVacancyDetails,
)

from tests.conftest import (
    create_test_user,
    get_auth_headers,
    set_tracked_vacancy_fields,
)


VALID_RESUME_TEXT = (
    "Python Backend Developer with commercial experience in FastAPI, "
    "PostgreSQL, SQLAlchemy, REST API integrations and AI applications."
)

VALID_VACANCY_TEXT = (
    "Python Backend Developer vacancy requiring FastAPI, PostgreSQL, "
    "SQLAlchemy, REST API experience and strong English skills."
)


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

    user_data = create_test_user(client, prefix="interaction")
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


def create_resume_sent_interaction(
    client,
    auth_headers: dict[str, str],
    tracked_vacancy_id: int,
    *,
    direction: str = "outgoing",
    occurred_at: str = "2026-08-18T09:30:00+00:00",
):
    """Create a resume-sent interaction response."""

    return client.post(
        f"/tracked-vacancies/{tracked_vacancy_id}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "resume_sent",
            "direction": direction,
            "message_text": "Please find my CV attached.",
            "occurred_at": occurred_at,
        },
    )


def test_create_interaction(client, monkeypatch):
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
    assert datetime.fromisoformat(interaction["occurred_at"]) == (
        datetime.fromisoformat(occurred_at)
    )
    assert interaction["id"] is not None
    assert interaction["created_at"] is not None
    assert interaction["updated_at"] is not None


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
        "message_text": "Recruiter called to discuss the position.",
        "summary": "Introductory recruiter call.",
        "occurred_at": "2026-08-19T11:00:00+00:00",
    }

    response = client.patch(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200
    assert response.json()["interaction_type"] == interaction["interaction_type"]
    assert response.json()["direction"] == interaction["direction"]
    assert response.json()["message_text"] == update_data["message_text"]
    assert response.json()["summary"] == update_data["summary"]
    assert datetime.fromisoformat(response.json()["occurred_at"]) == (
        datetime.fromisoformat(update_data["occurred_at"])
    )

    get_response = client.get(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["interaction_type"] == interaction["interaction_type"]
    assert get_response.json()["summary"] == update_data["summary"]


@pytest.mark.parametrize(
    "forbidden_field",
    [
        {"interaction_type": "call"},
        {"direction": "incoming"},
        {"summary": "Changed.", "direction": "outgoing"},
    ],
)
def test_update_interaction_rejects_type_and_direction(
    client,
    monkeypatch,
    forbidden_field,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    interaction = create_test_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
    )

    response = client.patch(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
        json=forbidden_field,
    )

    assert response.status_code == 422

    get_response = client.get(
        f"/tracked-vacancies/interactions/{interaction['id']}",
        headers=auth_headers,
    )

    assert get_response.json() == interaction


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
    other_user = create_test_user(client, prefix="interaction")
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


def test_resume_sent_updates_saved_tracked_vacancy(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unrelated_fields = {
        "priority": "high",
        "decision": "consider_later",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    update_response = client.patch(
        tracked_vacancy_path,
        headers=auth_headers,
        json=unrelated_fields,
    )
    assert update_response.status_code == 200
    occurred_at = "2026-08-18T09:30:00+00:00"

    response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at=occurred_at,
    )

    assert response.status_code == 201
    assert response.json()["interaction_type"] == "resume_sent"
    assert response.json()["direction"] == "outgoing"

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == "resume_sent"
    assert datetime.fromisoformat(tracked_data["applied_at"]) == (
        datetime.fromisoformat(occurred_at)
    )
    assert tracked_data["priority"] == unrelated_fields["priority"]
    assert tracked_data["decision"] == unrelated_fields["decision"]
    for field_name in ("closed_at", "next_action_at"):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unrelated_fields[field_name])
        )


def test_resume_sent_updates_analyzed_tracked_vacancy(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status="analyzed")
    occurred_at = "2026-08-18T10:30:00+00:00"

    response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at=occurred_at,
    )

    assert response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "resume_sent"
    assert datetime.fromisoformat(
        tracked_response.json()["applied_at"]
    ) == datetime.fromisoformat(occurred_at)


def test_resume_sent_does_not_roll_back_later_status(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status="screening")
    occurred_at = "2026-08-18T10:30:00+00:00"

    response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at=occurred_at,
    )

    assert response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "screening"
    assert datetime.fromisoformat(
        tracked_response.json()["applied_at"]
    ) == datetime.fromisoformat(occurred_at)


def test_resume_sent_rejects_incoming_direction(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )

    response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        direction="incoming",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "A resume_sent interaction must have outgoing direction."
    )

    tracked_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "saved"
    assert tracked_response.json()["applied_at"] is None
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


def test_cannot_create_duplicate_resume_sent_interaction(
    client,
    monkeypatch,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    first_occurred_at = "2026-08-18T09:30:00+00:00"
    first_response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at=first_occurred_at,
    )

    second_response = create_resume_sent_interaction(
        client,
        auth_headers,
        tracked_vacancy["id"],
        occurred_at="2026-08-19T09:30:00+00:00",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "A resume_sent interaction already exists for this tracked vacancy."
    )

    interactions_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=auth_headers,
    )
    tracked_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
    )

    assert interactions_response.status_code == 200
    assert len(interactions_response.json()) == 1
    assert tracked_response.status_code == 200
    assert datetime.fromisoformat(
        tracked_response.json()["applied_at"]
    ) == datetime.fromisoformat(first_occurred_at)


def test_failed_resume_sent_creation_keeps_tracked_vacancy_unchanged(
    client,
    monkeypatch,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )

    with monkeypatch.context() as commit_patch:
        commit_patch.setattr(
            AsyncSession,
            "commit",
            AsyncMock(side_effect=RuntimeError("Database commit failed")),
        )

        with pytest.raises(RuntimeError, match="Database commit failed"):
            create_resume_sent_interaction(
                client,
                auth_headers,
                tracked_vacancy["id"],
            )

    tracked_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "saved"
    assert tracked_response.json()["applied_at"] is None
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    (
        "initial_status",
        "interaction_type",
        "direction",
        "expected_status",
    ),
    [
        pytest.param(
            "resume_sent",
            "message",
            "incoming",
            "recruiter_contact",
            id="incoming-message-advances-status",
        ),
        pytest.param(
            "resume_sent",
            "call",
            "incoming",
            "recruiter_contact",
            id="incoming-call-advances-status",
        ),
        pytest.param(
            "resume_sent",
            "message",
            "outgoing",
            "resume_sent",
            id="outgoing-message-keeps-status",
        ),
        pytest.param(
            "resume_sent",
            "call",
            "outgoing",
            "resume_sent",
            id="outgoing-call-keeps-status",
        ),
        pytest.param(
            "saved",
            "message",
            "incoming",
            "recruiter_contact",
            id="incoming-message-advances-status-before-resume-sent",
        ),
        pytest.param(
            "analyzed",
            "call",
            "incoming",
            "recruiter_contact",
            id="incoming-call-advances-status-before-resume-sent",
        ),
        pytest.param(
            "screening",
            "message",
            "incoming",
            "screening",
            id="incoming-message-does-not-roll-back-screening",
        ),
        pytest.param(
            "interview",
            "call",
            "incoming",
            "interview",
            id="incoming-call-does-not-roll-back-interview",
        ),
    ],
)
def test_meaningful_interaction_advances_status_to_recruiter_contact(
    client,
    monkeypatch,
    initial_status,
    interaction_type,
    direction,
    expected_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-18T09:00:00+00:00",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        **unchanged_fields,
    )

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": interaction_type,
            "direction": direction,
            "message_text": "Meaningful recruiter communication.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201
    assert interaction_response.json()["interaction_type"] == (
        interaction_type
    )
    assert interaction_response.json()["direction"] == direction

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == expected_status
    assert tracked_data["priority"] == unchanged_fields["priority"]
    assert tracked_data["decision"] == unchanged_fields["decision"]
    for field_name in (
        "applied_at",
        "closed_at",
        "next_action_at",
    ):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


@pytest.mark.parametrize(
    "initial_status",
    [
        "resume_sent",
        "recruiter_contact",
        "screening",
        "interview",
        "test_task",
        "offer",
    ],
)
def test_incoming_rejection_closes_active_tracked_vacancy(
    client,
    monkeypatch,
    initial_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "applied_at": "2026-08-10T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        priority="high",
        decision="interested",
        **unchanged_fields,
    )
    occurred_at = "2026-08-20T10:00:00+00:00"

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "rejection",
            "direction": "incoming",
            "summary": "Employer rejected the application.",
            "occurred_at": occurred_at,
        },
    )

    assert interaction_response.status_code == 201
    interaction_data = interaction_response.json()
    assert interaction_data["interaction_type"] == "rejection"
    assert interaction_data["direction"] == "incoming"

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == "rejected"
    assert tracked_data["priority"] == "low"
    assert tracked_data["decision"] == "not_interested"
    assert datetime.fromisoformat(tracked_data["closed_at"]) == (
        datetime.fromisoformat(occurred_at)
    )
    assert datetime.fromisoformat(tracked_data["closed_at"]) != (
        datetime.fromisoformat(interaction_data["created_at"])
    )
    for field_name in ("applied_at", "next_action_at"):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


@pytest.mark.parametrize(
    "initial_status",
    [
        "resume_sent",
        "recruiter_contact",
        "screening",
        "interview",
        "test_task",
        "offer",
    ],
)
def test_outgoing_rejection_closes_active_tracked_vacancy(
    client,
    monkeypatch,
    initial_status,
):
    """A candidate can decline an offer or withdraw after contact was made."""

    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "applied_at": "2026-08-10T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        priority="high",
        decision="interested",
        **unchanged_fields,
    )
    occurred_at = "2026-08-20T10:00:00+00:00"

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "rejection",
            "direction": "outgoing",
            "summary": "Candidate declined and withdrew from the process.",
            "occurred_at": occurred_at,
        },
    )

    assert interaction_response.status_code == 201
    interaction_data = interaction_response.json()
    assert interaction_data["interaction_type"] == "rejection"
    assert interaction_data["direction"] == "outgoing"

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == "rejected"
    assert tracked_data["priority"] == "low"
    assert tracked_data["decision"] == "not_interested"
    assert datetime.fromisoformat(tracked_data["closed_at"]) == (
        datetime.fromisoformat(occurred_at)
    )
    for field_name in ("applied_at", "next_action_at"):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


def test_rejection_requires_direction(client, monkeypatch):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status="resume_sent")

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "rejection",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 400
    assert interaction_response.json()["detail"] == (
        "A rejection interaction must have a direction."
    )

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "resume_sent"
    assert tracked_response.json()["closed_at"] is None
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    "terminal_status",
    ["rejected", "discarded", "closed"],
)
def test_rejection_does_not_overwrite_terminal_tracked_vacancy(
    client,
    monkeypatch,
    terminal_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    terminal_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "closed_at": "2026-08-15T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=terminal_status,
        **terminal_fields,
    )

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "rejection",
            "direction": "incoming",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 409
    assert interaction_response.json()["detail"] == (
        "A rejection interaction cannot be created for a tracked "
        f"vacancy with status {terminal_status}."
    )

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == terminal_status
    assert tracked_data["priority"] == terminal_fields["priority"]
    assert tracked_data["decision"] == terminal_fields["decision"]
    for field_name in ("applied_at", "closed_at", "next_action_at"):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(terminal_fields[field_name])
        )
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


def test_failed_rejection_keeps_tracked_vacancy_unchanged(
    client,
    monkeypatch,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    original_fields = {
        "status": "resume_sent",
        "priority": "high",
        "decision": "interested",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(tracked_vacancy["id"], **original_fields)

    with monkeypatch.context() as commit_patch:
        commit_patch.setattr(
            AsyncSession,
            "commit",
            AsyncMock(side_effect=RuntimeError("Database commit failed")),
        )

        with pytest.raises(RuntimeError, match="Database commit failed"):
            client.post(
                f"{tracked_vacancy_path}/interactions",
                headers=auth_headers,
                data={
                    "interaction_type": "rejection",
                    "direction": "incoming",
                    "occurred_at": "2026-08-20T10:00:00+00:00",
                },
            )

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == original_fields["status"]
    assert tracked_data["priority"] == original_fields["priority"]
    assert tracked_data["decision"] == original_fields["decision"]
    assert tracked_data["closed_at"] is None
    for field_name in ("applied_at", "next_action_at"):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(original_fields[field_name])
        )
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    (
        "initial_status",
        "direction",
        "expected_status",
    ),
    [
        pytest.param(
            "resume_sent",
            "incoming",
            "screening",
            id="resume-sent-advances-to-screening",
        ),
        pytest.param(
            "recruiter_contact",
            "incoming",
            "screening",
            id="recruiter-contact-advances-to-screening",
        ),
        pytest.param(
            "recruiter_contact",
            "outgoing",
            "recruiter_contact",
            id="outgoing-questions-do-not-advance-status",
        ),
        pytest.param(
            "saved",
            "incoming",
            "screening",
            id="saved-advances-to-screening",
        ),
        pytest.param(
            "interview",
            "incoming",
            "interview",
            id="screening-does-not-roll-back-interview",
        ),
    ],
)
def test_screening_questions_update_only_eligible_statuses(
    client,
    monkeypatch,
    initial_status,
    direction,
    expected_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        **unchanged_fields,
    )

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "screening_questions",
            "direction": direction,
            "message_text": "Please answer the screening questions.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201
    assert interaction_response.json()["interaction_type"] == (
        "screening_questions"
    )
    assert interaction_response.json()["direction"] == direction

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == expected_status
    assert tracked_data["priority"] == unchanged_fields["priority"]
    assert tracked_data["decision"] == unchanged_fields["decision"]
    for field_name in (
        "applied_at",
        "closed_at",
        "next_action_at",
    ):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


@pytest.mark.parametrize(
    ("initial_status", "interaction_type"),
    [
        pytest.param(
            "resume_sent",
            "hr_interview",
            id="hr-interview-after-resume-sent",
        ),
        pytest.param(
            "recruiter_contact",
            "technical_interview",
            id="technical-interview-after-recruiter-contact",
        ),
        pytest.param(
            "screening",
            "final_interview",
            id="final-interview-after-screening",
        ),
        pytest.param(
            "test_task",
            "technical_interview",
            id="technical-interview-after-test-task",
        ),
    ],
)
def test_interview_events_advance_eligible_statuses(
    client,
    monkeypatch,
    initial_status,
    interaction_type,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        **unchanged_fields,
    )

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": interaction_type,
            "summary": "Interview completed.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201
    assert interaction_response.json()["interaction_type"] == (
        interaction_type
    )
    assert interaction_response.json()["direction"] is None

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == "interview"
    assert tracked_data["priority"] == unchanged_fields["priority"]
    assert tracked_data["decision"] == unchanged_fields["decision"]
    for field_name in (
        "applied_at",
        "closed_at",
        "next_action_at",
    ):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


def test_interview_event_keeps_existing_interview_status(
    client,
    monkeypatch,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status="interview")

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "final_interview",
            "summary": "Final interview completed.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "interview"


@pytest.mark.parametrize(
    ("initial_status", "interaction_type"),
    [
        pytest.param(
            "offer",
            "technical_interview",
            id="interview-does-not-roll-back-offer",
        ),
    ],
)
def test_interview_events_do_not_change_ineligible_statuses(
    client,
    monkeypatch,
    initial_status,
    interaction_type,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=initial_status)

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": interaction_type,
            "summary": "Historical interview event.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == initial_status


@pytest.mark.parametrize(
    ("initial_status", "direction", "expected_status"),
    [
        pytest.param(
            "resume_sent",
            "incoming",
            "test_task",
            id="test-task-after-resume-sent",
        ),
        pytest.param(
            "recruiter_contact",
            "incoming",
            "test_task",
            id="test-task-after-recruiter-contact",
        ),
        pytest.param(
            "screening",
            "incoming",
            "test_task",
            id="test-task-after-screening",
        ),
        pytest.param(
            "interview",
            "incoming",
            "test_task",
            id="test-task-after-interview",
        ),
        pytest.param(
            "interview",
            "outgoing",
            "interview",
            id="outgoing-test-task-keeps-status",
        ),
        pytest.param(
            "interview",
            None,
            "interview",
            id="test-task-without-direction-keeps-status",
        ),
        pytest.param(
            "offer",
            "incoming",
            "offer",
            id="test-task-does-not-roll-back-offer",
        ),
        pytest.param(
            "saved",
            "incoming",
            "test_task",
            id="incoming-test-task-advances-saved",
        ),
        pytest.param(
            "analyzed",
            "incoming",
            "test_task",
            id="incoming-test-task-advances-analyzed",
        ),
        pytest.param(
            "saved",
            "outgoing",
            "saved",
            id="outgoing-test-task-keeps-saved",
        ),
    ],
)
def test_test_task_interactions_update_only_eligible_statuses(
    client,
    monkeypatch,
    initial_status,
    direction,
    expected_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        **unchanged_fields,
    )
    interaction_data = {
        "interaction_type": "test_task",
        "summary": "Test task event.",
        "occurred_at": "2026-08-20T10:00:00+00:00",
    }
    if direction is not None:
        interaction_data["direction"] = direction

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data=interaction_data,
    )

    assert interaction_response.status_code == 201
    assert interaction_response.json()["interaction_type"] == "test_task"
    assert interaction_response.json()["direction"] == direction

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == expected_status
    assert tracked_data["priority"] == unchanged_fields["priority"]
    assert tracked_data["decision"] == unchanged_fields["decision"]
    for field_name in (
        "applied_at",
        "closed_at",
        "next_action_at",
    ):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


@pytest.mark.parametrize(
    ("initial_status", "expected_status"),
    [
        pytest.param("resume_sent", "offer", id="offer-after-resume-sent"),
        pytest.param(
            "recruiter_contact",
            "offer",
            id="offer-after-recruiter-contact",
        ),
        pytest.param("screening", "offer", id="offer-after-screening"),
        pytest.param("interview", "offer", id="offer-after-interview"),
        pytest.param("test_task", "offer", id="offer-after-test-task"),
        pytest.param("offer", "offer", id="revised-offer-keeps-status"),
    ],
)
def test_incoming_offer_updates_only_eligible_statuses(
    client,
    monkeypatch,
    initial_status,
    expected_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    unchanged_fields = {
        "priority": "high",
        "decision": "consider_later",
        "applied_at": "2026-08-10T09:00:00+00:00",
        "closed_at": "2026-08-25T09:00:00+00:00",
        "next_action_at": "2026-08-30T09:00:00+00:00",
    }
    set_tracked_vacancy_fields(
        tracked_vacancy["id"],
        status=initial_status,
        **unchanged_fields,
    )

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "offer",
            "direction": "incoming",
            "summary": "Employer sent an offer.",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    tracked_data = tracked_response.json()
    assert tracked_data["status"] == expected_status
    assert tracked_data["priority"] == unchanged_fields["priority"]
    assert tracked_data["decision"] == unchanged_fields["decision"]
    for field_name in (
        "applied_at",
        "closed_at",
        "next_action_at",
    ):
        assert datetime.fromisoformat(tracked_data[field_name]) == (
            datetime.fromisoformat(unchanged_fields[field_name])
        )


@pytest.mark.parametrize("direction", ["outgoing", None])
def test_offer_rejects_non_incoming_direction(
    client,
    monkeypatch,
    direction,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status="interview")
    interaction_data = {
        "interaction_type": "offer",
        "occurred_at": "2026-08-20T10:00:00+00:00",
    }
    if direction is not None:
        interaction_data["direction"] = direction

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data=interaction_data,
    )

    assert interaction_response.status_code == 400
    assert interaction_response.json()["detail"] == (
        "An offer interaction must have incoming direction."
    )

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == "interview"
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    "terminal_status",
    ["rejected", "discarded", "closed"],
)
def test_offer_does_not_overwrite_terminal_status(
    client,
    monkeypatch,
    terminal_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=terminal_status)

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "offer",
            "direction": "incoming",
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 409
    assert interaction_response.json()["detail"] == (
        "An offer interaction cannot be created for a tracked "
        f"vacancy with status {terminal_status}."
    )

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["status"] == terminal_status
    assert interactions_response.status_code == 200
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    ("initial_status", "interaction_type", "direction"),
    [
        ("saved", "hr_interview", None),
        ("saved", "offer", "incoming"),
        ("analyzed", "offer_discussion", None),
    ],
)
def test_progress_interactions_require_first_contact(
    client,
    monkeypatch,
    initial_status,
    interaction_type,
    direction,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=initial_status)

    form_data = {
        "interaction_type": interaction_type,
        "occurred_at": "2026-08-20T10:00:00+00:00",
    }
    if direction is not None:
        form_data["direction"] = direction

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data=form_data,
    )

    assert interaction_response.status_code == 409
    assert "cannot be created" in interaction_response.json()["detail"]
    assert initial_status in interaction_response.json()["detail"]

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.json()["status"] == initial_status
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    ("terminal_status", "interaction_type", "direction"),
    [
        ("rejected", "test_task", "incoming"),
        ("discarded", "hr_interview", None),
        ("closed", "resume_sent", "outgoing"),
    ],
)
def test_terminal_tracked_vacancy_rejects_progress_interactions(
    client,
    monkeypatch,
    terminal_status,
    interaction_type,
    direction,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=terminal_status)

    form_data = {
        "interaction_type": interaction_type,
        "occurred_at": "2026-08-20T10:00:00+00:00",
    }
    if direction is not None:
        form_data["direction"] = direction

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data=form_data,
    )

    assert interaction_response.status_code == 409

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )
    interactions_response = client.get(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
    )

    assert tracked_response.json()["status"] == terminal_status
    assert interactions_response.json() == []


@pytest.mark.parametrize(
    ("terminal_status", "interaction_type", "direction"),
    [
        ("rejected", "message", "incoming"),
        ("discarded", "call", "incoming"),
        ("closed", "feedback", "incoming"),
    ],
)
def test_terminal_tracked_vacancy_accepts_history_only_interactions(
    client,
    monkeypatch,
    terminal_status,
    interaction_type,
    direction,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=terminal_status)

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": interaction_type,
            "direction": direction,
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.json()["status"] == terminal_status


@pytest.mark.parametrize(
    ("initial_status", "direction", "expected_status"),
    [
        pytest.param(
            "saved",
            "incoming",
            "recruiter_contact",
            id="invitation-is-first-contact-from-saved",
        ),
        pytest.param(
            "analyzed",
            "incoming",
            "recruiter_contact",
            id="invitation-is-first-contact-from-analyzed",
        ),
        pytest.param(
            "resume_sent",
            "incoming",
            "recruiter_contact",
            id="invitation-is-first-contact-from-resume-sent",
        ),
        pytest.param(
            "saved",
            "outgoing",
            "saved",
            id="outgoing-invitation-keeps-status",
        ),
        pytest.param(
            "screening",
            "incoming",
            "screening",
            id="invitation-does-not-roll-back-screening",
        ),
    ],
)
def test_incoming_interview_invitation_is_first_contact(
    client,
    monkeypatch,
    initial_status,
    direction,
    expected_status,
):
    auth_headers, tracked_vacancy = prepare_interaction_data(
        client,
        monkeypatch,
    )
    tracked_vacancy_path = f"/tracked-vacancies/{tracked_vacancy['id']}"
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=initial_status)

    interaction_response = client.post(
        f"{tracked_vacancy_path}/interactions",
        headers=auth_headers,
        data={
            "interaction_type": "interview_invitation",
            "direction": direction,
            "occurred_at": "2026-08-20T10:00:00+00:00",
        },
    )

    assert interaction_response.status_code == 201

    tracked_response = client.get(
        tracked_vacancy_path,
        headers=auth_headers,
    )

    assert tracked_response.json()["status"] == expected_status
