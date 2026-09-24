from unittest.mock import AsyncMock

from app.core.exceptions import AIServiceError
from app.schemas.ai_outputs import ParsedVacancyAnalysis, ParsedVacancyDetails

from tests.conftest import create_test_user, get_auth_headers


VALID_VACANCY_TEXT = (
    "Python Backend Developer vacancy requiring FastAPI, PostgreSQL, "
    "SQLAlchemy, REST API experience and strong English skills."
)


def mock_vacancy_parser(monkeypatch):
    """Mock AI vacancy parsing and return deterministic vacancy data."""

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
            salary_min=2500,
            salary_max=4000,
            currency="USD",
            cleaned_text=VALID_VACANCY_TEXT,
        )

    monkeypatch.setattr(
        "app.services.vacancy_service.parse_vacancy_chain",
        mock_parse_vacancy_chain,
    )


def create_test_vacancy(client, auth_headers, monkeypatch) -> dict:
    """Create and return a vacancy with mocked AI parsing."""

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


def test_create_vacancy_from_text(client, monkeypatch):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
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

    response_data = response.json()
    vacancy = response_data["vacancy"]

    assert vacancy["company_name"] == "Test Company"
    assert vacancy["position_title"] == "Python Backend Developer"
    assert vacancy["source"] == "company_site"
    assert vacancy["location"] == "Kyiv"
    assert vacancy["work_format"] == "remote"
    assert vacancy["salary_min"] == 2500
    assert vacancy["salary_max"] == 4000
    assert vacancy["currency"] == "USD"
    assert vacancy["raw_text"] == VALID_VACANCY_TEXT
    assert response_data["analysis"] is None


def test_create_vacancy_rejects_too_short_text(client):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)

    response = client.post(
        "/vacancies/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content="Too short vacancy text.",
    )

    assert response.status_code == 422


def test_create_vacancy_rejects_too_long_text(client):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)

    too_long_text = "a" * 20001

    response = client.post(
        "/vacancies/from-text",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=too_long_text,
    )

    assert response.status_code == 422


def test_create_vacancy_from_text_with_analyze_true(client, monkeypatch):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
    mock_vacancy_parser(monkeypatch)

    monkeypatch.setattr(
        "app.services.vacancy_service.analyze_vacancy_chain",
        AsyncMock(
            return_value=ParsedVacancyAnalysis(
                experience_level="middle",
                english_level="B2",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                optional_skills=["Docker"],
                responsibilities=["Develop backend APIs"],
                red_flags=[],
                green_flags=["Remote work"],
                summary="Backend role with a Python-focused stack.",
                recommendation="recommended",
            )
        ),
    )
    monkeypatch.setattr(
        "app.services.vacancy_service.create_or_update_vacancy_embedding",
        AsyncMock(),
    )

    response = client.post(
        "/vacancies/from-text",
        params={"analyze": True},
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_VACANCY_TEXT,
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["vacancy"]["company_name"] == "Test Company"
    assert response_data["analysis"] is not None
    assert response_data["analysis"]["experience_level"] == "middle"


def test_create_vacancy_from_text_returns_vacancy_when_analysis_fails(
    client,
    monkeypatch,
):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
    mock_vacancy_parser(monkeypatch)

    monkeypatch.setattr(
        "app.services.vacancy_service.analyze_vacancy_chain",
        AsyncMock(side_effect=AIServiceError("AI analysis failed")),
    )

    response = client.post(
        "/vacancies/from-text",
        params={"analyze": True},
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
        content=VALID_VACANCY_TEXT,
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["vacancy"]["company_name"] == "Test Company"
    assert response_data["analysis"] is None

    vacancy_id = response_data["vacancy"]["id"]

    # The vacancy is not lost: a client can retrieve it and retry analysis
    # separately instead of re-submitting the text and duplicating it.
    get_response = client.get(
        f"/vacancies/{vacancy_id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == vacancy_id


def test_create_vacancy_requires_authentication(client):
    response = client.post(
        "/vacancies/from-text",
        headers={"Content-Type": "text/plain"},
        content=VALID_VACANCY_TEXT,
    )

    assert response.status_code == 401


def test_get_vacancies_returns_all(client, monkeypatch):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)

    first_vacancy = create_test_vacancy(client, auth_headers, monkeypatch)
    second_vacancy = create_test_vacancy(client, auth_headers, monkeypatch)

    response = client.get("/vacancies", headers=auth_headers)

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 2
    assert {vacancy["id"] for vacancy in response_data} == {
        first_vacancy["id"],
        second_vacancy["id"],
    }
    # Newest vacancy comes first.
    assert response_data[0]["id"] == second_vacancy["id"]
    assert response_data[1]["id"] == first_vacancy["id"]

    # The list is a lightweight summary, not the full vacancy.
    assert "raw_text" not in response_data[0]
    assert "cleaned_text" not in response_data[0]
    assert "source_url" not in response_data[0]
    assert "salary_min" not in response_data[0]
    assert "salary_max" not in response_data[0]
    assert "currency" not in response_data[0]
    assert "created_at" not in response_data[0]

    assert response_data[0]["company_name"] == "Test Company"
    assert response_data[0]["position_title"] == (
        "Python Backend Developer"
    )
    assert response_data[0]["source"] == "company_site"
    assert response_data[0]["location"] == "Kyiv"
    assert response_data[0]["work_format"] == "remote"
    assert response_data[0]["employment_type"] == "full-time"


def test_get_vacancies_requires_authentication(client):
    response = client.get("/vacancies")

    assert response.status_code == 401


def test_get_vacancies_visible_to_another_authenticated_user(
    client,
    monkeypatch,
):
    owner_data = create_test_user(client, prefix="vacancy")
    owner_auth_headers = get_auth_headers(client, owner_data)
    created_vacancy = create_test_vacancy(
        client, owner_auth_headers, monkeypatch
    )

    other_user = create_test_user(client, prefix="vacancy")
    other_auth_headers = get_auth_headers(client, other_user)

    response = client.get("/vacancies", headers=other_auth_headers)

    assert response.status_code == 200
    assert created_vacancy["id"] in {
        vacancy["id"] for vacancy in response.json()
    }


def test_get_vacancy_by_id(client, monkeypatch):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
    created_vacancy = create_test_vacancy(
        client,
        auth_headers,
        monkeypatch,
    )

    response = client.get(
        f"/vacancies/{created_vacancy['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == created_vacancy


def test_get_nonexistent_vacancy_returns_404(client):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)

    response = client.get(
        "/vacancies/999999",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Vacancy not found"


def test_get_vacancy_requires_authentication(client):
    response = client.get("/vacancies/1")

    assert response.status_code == 401


def test_vacancy_is_visible_to_another_authenticated_user(
    client,
    monkeypatch,
):
    first_user = create_test_user(client, prefix="vacancy")
    first_user_headers = get_auth_headers(client, first_user)

    created_vacancy = create_test_vacancy(
        client,
        first_user_headers,
        monkeypatch,
    )

    second_user = create_test_user(client, prefix="vacancy")
    second_user_headers = get_auth_headers(client, second_user)

    response = client.get(
        f"/vacancies/{created_vacancy['id']}",
        headers=second_user_headers,
    )

    assert response.status_code == 200
    assert response.json() == created_vacancy


def test_create_vacancy_analysis_creates_embedding(client, monkeypatch):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
    vacancy = create_test_vacancy(client, auth_headers, monkeypatch)

    monkeypatch.setattr(
        "app.services.vacancy_service.analyze_vacancy_chain",
        AsyncMock(
            return_value=ParsedVacancyAnalysis(
                experience_level="middle",
                english_level="B2",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                optional_skills=["Docker"],
                responsibilities=["Develop backend APIs"],
                red_flags=[],
                green_flags=["Remote work"],
                summary="Backend role with a Python-focused stack.",
                recommendation="recommended",
            )
        ),
    )
    embedding_mock = AsyncMock()
    monkeypatch.setattr(
        "app.services.vacancy_service.create_or_update_vacancy_embedding",
        embedding_mock,
    )

    response = client.post(
        f"/vacancies/{vacancy['id']}/analysis",
        headers=auth_headers,
    )

    assert response.status_code == 201

    analysis = response.json()["analysis"]
    embedding_mock.assert_awaited_once()
    embedding_call = embedding_mock.await_args.kwargs

    assert embedding_call["vacancy"].id == vacancy["id"]
    assert embedding_call["vacancy_analysis"].id == analysis["id"]


def test_embedding_failure_does_not_cancel_vacancy_analysis(
    client,
    monkeypatch,
):
    user_data = create_test_user(client, prefix="vacancy")
    auth_headers = get_auth_headers(client, user_data)
    vacancy = create_test_vacancy(client, auth_headers, monkeypatch)

    monkeypatch.setattr(
        "app.services.vacancy_service.analyze_vacancy_chain",
        AsyncMock(
            return_value=ParsedVacancyAnalysis(
                experience_level="middle",
                english_level="B2",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                optional_skills=["Docker"],
                responsibilities=["Develop backend APIs"],
                red_flags=[],
                green_flags=["Remote work"],
                summary="Backend role with a Python-focused stack.",
                recommendation="recommended",
            )
        ),
    )
    embedding_mock = AsyncMock(
        side_effect=AIServiceError("Embedding provider failed"),
    )
    monkeypatch.setattr(
        "app.services.vacancy_service.create_or_update_vacancy_embedding",
        embedding_mock,
    )

    create_response = client.post(
        f"/vacancies/{vacancy['id']}/analysis",
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    embedding_mock.assert_awaited_once()

    created_analysis = create_response.json()["analysis"]

    get_response = client.get(
        f"/vacancies/{vacancy['id']}/analysis",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_analysis["id"]
