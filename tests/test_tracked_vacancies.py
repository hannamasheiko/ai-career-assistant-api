from datetime import datetime, timezone

import pytest

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
            "full_name": "Tracked Vacancy Test Candidate",
            "email": user_data["email"],
        },
    )

    assert response.status_code == 201

    return response.json()


def mock_resume_parser(monkeypatch) -> None:
    """Mock AI resume parsing with deterministic structured data."""

    async def mock_parse_resume_chain(raw_text: str):
        assert raw_text == VALID_RESUME_TEXT

        return ParsedResume(
            resume_analysis=ParsedResumeAnalysis(
                full_name="Tracked Vacancy Test Candidate",
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


def create_test_resume(client, auth_headers, monkeypatch) -> dict:
    """Create and return a persisted resume with mocked AI parsing."""

    mock_resume_parser(monkeypatch)

    response = client.post(
        "/resumes/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_RESUME_TEXT,
    )

    assert response.status_code == 201

    return response.json()["resume_document"]


def create_test_vacancy(client, auth_headers, monkeypatch) -> dict:
    """Create and return a persisted vacancy with mocked AI parsing."""

    mock_vacancy_parser(monkeypatch)

    response = client.post(
        "/vacancies/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_VACANCY_TEXT,
    )

    assert response.status_code == 201

    return response.json()["vacancy"]


def create_test_tracked_vacancy(
    client,
    auth_headers: dict[str, str],
    resume_document_id: int,
    vacancy_id: int,
) -> dict:
    """Create and return a tracked vacancy."""

    response = client.post(
        "/tracked-vacancies",
        headers=auth_headers,
        json={
            "resume_document_id": resume_document_id,
            "vacancy_id": vacancy_id,
        },
    )

    assert response.status_code == 201

    return response.json()


def prepare_tracked_vacancy_data(client, monkeypatch):
    """Create the authenticated user, resume, and global vacancy."""

    user_data = create_test_user(client, prefix="tracked")
    auth_headers = get_auth_headers(client, user_data)
    create_test_profile(client, auth_headers, user_data)
    resume = create_test_resume(client, auth_headers, monkeypatch)
    vacancy = create_test_vacancy(client, auth_headers, monkeypatch)

    return auth_headers, resume, vacancy


def test_create_tracked_vacancy(client, monkeypatch):
    auth_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )

    response = client.post(
        "/tracked-vacancies",
        headers=auth_headers,
        json={
            "resume_document_id": resume["id"],
            "vacancy_id": vacancy["id"],
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["resume_document_id"] == resume["id"]
    assert response_data["vacancy_id"] == vacancy["id"]
    assert response_data["status"] == "saved"
    assert response_data["priority"] == "low"
    assert response_data["decision"] == "interested"
    assert response_data["notes"] is None


def test_create_tracked_vacancy_requires_authentication(client):
    response = client.post(
        "/tracked-vacancies",
        json={
            "resume_document_id": 1,
            "vacancy_id": 1,
        },
    )

    assert response.status_code == 401


def test_cannot_track_vacancy_with_another_users_resume(
    client,
    monkeypatch,
):
    first_user_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )

    second_user = create_test_user(client, prefix="tracked")
    second_user_headers = get_auth_headers(client, second_user)

    response = client.post(
        "/tracked-vacancies",
        headers=second_user_headers,
        json={
            "resume_document_id": resume["id"],
            "vacancy_id": vacancy["id"],
        },
    )

    assert first_user_headers != second_user_headers
    assert response.status_code == 404
    assert response.json()["detail"] == "Resume document not found."


def test_cannot_track_same_vacancy_twice_for_same_resume(
    client,
    monkeypatch,
):
    auth_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )
    request_data = {
        "resume_document_id": resume["id"],
        "vacancy_id": vacancy["id"],
    }

    first_response = client.post(
        "/tracked-vacancies",
        headers=auth_headers,
        json=request_data,
    )
    second_response = client.post(
        "/tracked-vacancies",
        headers=auth_headers,
        json=request_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "This vacancy is already tracked for this resume."
    )


def test_user_can_only_get_own_tracked_vacancies(
    client,
    monkeypatch,
):
    owner_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )
    tracked_vacancy = create_test_tracked_vacancy(
        client,
        owner_headers,
        resume["id"],
        vacancy["id"],
    )

    other_user = create_test_user(client, prefix="tracked")
    other_user_headers = get_auth_headers(client, other_user)

    owner_list_response = client.get(
        "/tracked-vacancies",
        headers=owner_headers,
    )
    other_user_list_response = client.get(
        "/tracked-vacancies",
        headers=other_user_headers,
    )
    other_user_get_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=other_user_headers,
    )

    assert owner_list_response.status_code == 200
    assert owner_list_response.json() == [tracked_vacancy]

    assert other_user_list_response.status_code == 200
    assert other_user_list_response.json() == []

    assert other_user_get_response.status_code == 404
    assert other_user_get_response.json()["detail"] == (
        "Tracked vacancy not found."
    )


def test_update_tracked_vacancy(client, monkeypatch):
    auth_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )
    tracked_vacancy = create_test_tracked_vacancy(
        client,
        auth_headers,
        resume["id"],
        vacancy["id"],
    )
    update_data = {
        "priority": "high",
        "decision": "interested",
        "notes": "Applied through company website.",
        "next_action_at": "2026-08-26T12:00:00+00:00",
    }

    response = client.patch(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "saved"
    assert response_data["priority"] == "high"
    assert response_data["decision"] == "interested"
    assert response_data["notes"] == "Applied through company website."
    assert datetime.fromisoformat(response_data["next_action_at"]) == (
        datetime.fromisoformat(update_data["next_action_at"])
    )

    get_response = client.get(
        f"/tracked-vacancies/{tracked_vacancy['id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "saved"
    assert get_response.json()["priority"] == "high"
    assert get_response.json()["notes"] == (
        "Applied through company website."
    )
    assert datetime.fromisoformat(get_response.json()["next_action_at"]) == (
        datetime.fromisoformat(update_data["next_action_at"])
    )


def prepare_tracked_vacancy_for_status_change(client, monkeypatch, status):
    """Create a tracked vacancy and force its status directly in the DB."""

    auth_headers, resume, vacancy = prepare_tracked_vacancy_data(
        client,
        monkeypatch,
    )
    tracked_vacancy = create_test_tracked_vacancy(
        client,
        auth_headers,
        resume["id"],
        vacancy["id"],
    )
    set_tracked_vacancy_fields(tracked_vacancy["id"], status=status)

    return auth_headers, f"/tracked-vacancies/{tracked_vacancy['id']}"


@pytest.mark.parametrize("target_status", ["discarded", "closed"])
@pytest.mark.parametrize("initial_status", ["saved", "interview", "offer"])
def test_discarded_and_closed_can_be_set_manually_and_stamp_closed_at(
    client,
    monkeypatch,
    initial_status,
    target_status,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        initial_status,
    )
    before = datetime.now(timezone.utc)

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": target_status},
    )

    assert response.status_code == 200
    assert response.json()["status"] == target_status
    assert datetime.fromisoformat(response.json()["closed_at"]) >= before


def test_manual_close_keeps_explicit_closed_at(client, monkeypatch):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        "interview",
    )

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": "closed", "closed_at": "2026-08-01T09:00:00+00:00"},
    )

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["closed_at"]) == (
        datetime.fromisoformat("2026-08-01T09:00:00+00:00")
    )


@pytest.mark.parametrize(
    "target_status",
    [
        "analyzed",
        "resume_sent",
        "recruiter_contact",
        "screening",
        "interview",
        "test_task",
        "offer",
        "rejected",
    ],
)
def test_interaction_driven_statuses_cannot_be_set_manually(
    client,
    monkeypatch,
    target_status,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        "saved",
    )

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": target_status, "notes": "Should not be saved."},
    )

    assert response.status_code == 409
    assert "cannot be changed manually" in response.json()["detail"]

    get_response = client.get(path, headers=auth_headers)

    assert get_response.json()["status"] == "saved"
    assert get_response.json()["notes"] is None


@pytest.mark.parametrize("closed_status", ["discarded", "closed"])
@pytest.mark.parametrize("reopen_status", ["saved", "analyzed"])
def test_closed_tracked_vacancy_can_be_reopened_and_clears_closed_at(
    client,
    monkeypatch,
    closed_status,
    reopen_status,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        closed_status,
    )
    close_response = client.patch(
        path,
        headers=auth_headers,
        json={"status": closed_status, "closed_at": "2026-08-01T09:00:00+00:00"},
    )
    assert close_response.status_code == 200

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": reopen_status},
    )

    assert response.status_code == 200
    assert response.json()["status"] == reopen_status
    assert response.json()["closed_at"] is None


def test_closed_tracked_vacancy_cannot_jump_to_interaction_status(
    client,
    monkeypatch,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        "closed",
    )

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": "interview"},
    )

    assert response.status_code == 409


def test_rejected_tracked_vacancy_cannot_be_reopened_by_patch(
    client,
    monkeypatch,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        "rejected",
    )

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": "saved"},
    )

    assert response.status_code == 409

    get_response = client.get(path, headers=auth_headers)

    assert get_response.json()["status"] == "rejected"


def test_patch_with_unchanged_status_still_updates_other_fields(
    client,
    monkeypatch,
):
    auth_headers, path = prepare_tracked_vacancy_for_status_change(
        client,
        monkeypatch,
        "interview",
    )

    response = client.patch(
        path,
        headers=auth_headers,
        json={"status": "interview", "priority": "high"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "interview"
    assert response.json()["priority"] == "high"
    assert response.json()["closed_at"] is None
