import uuid
from unittest.mock import AsyncMock

from app.ai.prompts.match_analysis import MATCH_ANALYSIS_PROMPT_VERSION
from app.schemas.ai_outputs import (
    ParsedMatchAnalysis,
    ParsedResume,
    ParsedResumeAnalysis,
    ParsedResumeSection,
    ParsedVacancyAnalysis,
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
        "username": f"match_user_{unique_suffix}",
        "email": f"match_{unique_suffix}@example.com",
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

    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
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
            "full_name": "Match Analysis Test Candidate",
            "email": user_data["email"],
            "location": "Kyiv",
            "preferred_work_formats": ["remote"],
            "desired_roles": ["Python Backend Developer"],
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
                full_name="Match Analysis Test Candidate",
                target_role="Python Backend Developer",
                english_level="B2",
                location="Kyiv",
                skills=["Python", "FastAPI", "PostgreSQL"],
                summary="Python backend developer.",
            ),
            sections=[
                ParsedResumeSection(
                    section_type="skills",
                    title="Skills",
                    content="Python, FastAPI, PostgreSQL",
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


def mock_vacancy_analysis(monkeypatch) -> None:
    """Mock AI vacancy analysis with deterministic structured data."""

    async def mock_analyze_vacancy_chain(vacancy_text: str):
        assert vacancy_text == VALID_VACANCY_TEXT

        return ParsedVacancyAnalysis(
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

    monkeypatch.setattr(
        "app.services.vacancy_service.analyze_vacancy_chain",
        mock_analyze_vacancy_chain,
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


def create_test_vacancy_analysis(
    client,
    auth_headers,
    vacancy_id: int,
    monkeypatch,
) -> dict:
    """Create and return a persisted vacancy analysis with mocked AI."""

    mock_vacancy_analysis(monkeypatch)

    response = client.post(
        f"/vacancies/{vacancy_id}/analysis",
        headers=auth_headers,
    )

    assert response.status_code == 201

    return response.json()["analysis"]


def create_test_tracked_vacancy(
    client,
    auth_headers,
    resume_document_id: int,
    vacancy_id: int,
) -> dict:
    """Create and return a persisted tracked vacancy."""

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


def prepare_match_analysis_data(
    client,
    monkeypatch,
    *,
    with_vacancy_analysis: bool = True,
) -> dict:
    """Create all persisted data required for match analysis tests."""

    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile = create_test_profile(client, auth_headers, user_data)
    resume = create_test_resume(client, auth_headers, monkeypatch)
    vacancy = create_test_vacancy(client, auth_headers, monkeypatch)

    vacancy_analysis = None
    if with_vacancy_analysis:
        vacancy_analysis = create_test_vacancy_analysis(
            client,
            auth_headers,
            vacancy["id"],
            monkeypatch,
        )

    tracked_vacancy = create_test_tracked_vacancy(
        client,
        auth_headers,
        resume["id"],
        vacancy["id"],
    )

    return {
        "auth_headers": auth_headers,
        "profile": profile,
        "resume": resume,
        "vacancy": vacancy,
        "vacancy_analysis": vacancy_analysis,
        "tracked_vacancy": tracked_vacancy,
    }


def build_match_analysis_result(
    *,
    match_score: int = 82,
    recommendation: str = "good_match",
) -> ParsedMatchAnalysis:
    """Build deterministic structured match analysis output."""

    return ParsedMatchAnalysis(
        match_score=match_score,
        recommendation=recommendation,
        strong_matches=["Python", "FastAPI"],
        partial_matches=["PostgreSQL"],
        missing_skills=["Docker"],
        risk_points=["Limited cloud experience"],
        reasoning_summary=(
            "The candidate matches most core requirements."
        ),
    )


def test_create_match_analysis(client, monkeypatch):
    test_data = prepare_match_analysis_data(client, monkeypatch)
    expected_result = build_match_analysis_result()

    async def mock_parse_match_analysis_chain(
        candidate_profile,
        resume_analysis,
        resume_sections,
        vacancy,
        vacancy_analysis,
        resume_text,
        vacancy_text,
    ):
        assert candidate_profile.id == test_data["profile"]["id"]
        assert resume_analysis.resume_document_id == test_data["resume"]["id"]
        assert len(resume_sections) == 1
        assert resume_sections[0].section_type == "skills"
        assert vacancy.id == test_data["vacancy"]["id"]
        assert vacancy_analysis.id == test_data["vacancy_analysis"]["id"]
        assert resume_text == VALID_RESUME_TEXT
        assert vacancy_text == VALID_VACANCY_TEXT

        return expected_result

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        mock_parse_match_analysis_chain,
    )

    response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["tracked_vacancy_id"] == (
        test_data["tracked_vacancy"]["id"]
    )
    assert response_data["match_score"] == 82
    assert response_data["recommendation"] == "good_match"
    assert response_data["strong_matches"] == ["Python", "FastAPI"]
    assert response_data["partial_matches"] == ["PostgreSQL"]
    assert response_data["missing_skills"] == ["Docker"]
    assert response_data["risk_points"] == ["Limited cloud experience"]
    assert response_data["ai_model"] is not None
    assert response_data["prompt_version"] == MATCH_ANALYSIS_PROMPT_VERSION


def test_get_match_analysis(client, monkeypatch):
    test_data = prepare_match_analysis_data(client, monkeypatch)

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        AsyncMock(return_value=build_match_analysis_result()),
    )

    create_response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert create_response.status_code == 201

    get_response = client.get(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert get_response.status_code == 200
    assert get_response.json() == create_response.json()


def test_get_match_analysis_returns_404_when_not_generated(
    client,
    monkeypatch,
):
    test_data = prepare_match_analysis_data(client, monkeypatch)

    response = client.get(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Match analysis not found."


def test_create_match_analysis_requires_vacancy_analysis(
    client,
    monkeypatch,
):
    test_data = prepare_match_analysis_data(
        client,
        monkeypatch,
        with_vacancy_analysis=False,
    )
    match_analysis_mock = AsyncMock()

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        match_analysis_mock,
    )

    response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Vacancy analysis is required before match analysis"
    )
    match_analysis_mock.assert_not_awaited()


def test_other_user_cannot_access_match_analysis(
    client,
    monkeypatch,
):
    test_data = prepare_match_analysis_data(client, monkeypatch)

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        AsyncMock(return_value=build_match_analysis_result()),
    )

    create_response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis",
        headers=test_data["auth_headers"],
    )

    assert create_response.status_code == 201

    other_user = create_test_user(client)
    other_user_headers = get_auth_headers(client, other_user)
    match_analysis_path = (
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis"
    )

    get_response = client.get(
        match_analysis_path,
        headers=other_user_headers,
    )
    post_response = client.post(
        match_analysis_path,
        headers=other_user_headers,
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Tracked vacancy not found."

    assert post_response.status_code == 404
    assert post_response.json()["detail"] == "Tracked vacancy not found."


def test_regenerate_match_analysis_updates_existing_record(
    client,
    monkeypatch,
):
    test_data = prepare_match_analysis_data(client, monkeypatch)
    results = iter(
        [
            build_match_analysis_result(
                match_score=65,
                recommendation="partial_match",
            ),
            build_match_analysis_result(
                match_score=85,
                recommendation="strong_match",
            ),
        ]
    )

    async def mock_parse_match_analysis_chain(**kwargs):
        return next(results)

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        mock_parse_match_analysis_chain,
    )

    match_analysis_path = (
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}/match-analysis"
    )

    first_response = client.post(
        match_analysis_path,
        headers=test_data["auth_headers"],
    )
    second_response = client.post(
        match_analysis_path,
        headers=test_data["auth_headers"],
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_data = first_response.json()
    second_data = second_response.json()

    assert second_data["id"] == first_data["id"]
    assert second_data["tracked_vacancy_id"] == first_data["tracked_vacancy_id"]
    assert first_data["match_score"] == 65
    assert first_data["recommendation"] == "partial_match"
    assert second_data["match_score"] == 85
    assert second_data["recommendation"] == "strong_match"

    get_response = client.get(
        match_analysis_path,
        headers=test_data["auth_headers"],
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == first_data["id"]
    assert get_response.json()["match_score"] == 85
    assert get_response.json()["recommendation"] == "strong_match"
