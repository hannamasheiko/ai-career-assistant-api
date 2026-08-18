import uuid
from unittest.mock import AsyncMock

from app.ai.prompts.content_generation import (
    GENERATED_CONTENT_PROMPT_VERSION,
)
from app.schemas.ai_outputs import (
    ParsedGeneratedContent,
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

GENERATED_COVER_LETTER = (
    "Dear Hiring Manager, I am interested in the Python Backend Developer "
    "position at Test Company."
)


def create_test_user(client) -> dict:
    """Create and return a registered test user."""

    unique_suffix = uuid.uuid4().hex[:8]

    user_data = {
        "username": f"content_user_{unique_suffix}",
        "email": f"content_{unique_suffix}@example.com",
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
            "full_name": "Generated Content Test Candidate",
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
                full_name="Generated Content Test Candidate",
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


def create_test_match_analysis(
    client,
    auth_headers,
    tracked_vacancy_id: int,
    vacancy_id: int,
    monkeypatch,
) -> dict:
    """Create and return a persisted match analysis with mocked AI."""

    mock_vacancy_analysis(monkeypatch)

    vacancy_analysis_response = client.post(
        f"/vacancies/{vacancy_id}/analysis",
        headers=auth_headers,
    )

    assert vacancy_analysis_response.status_code == 201

    monkeypatch.setattr(
        "app.services.match_analysis_service.parse_match_analysis_chain",
        AsyncMock(
            return_value=ParsedMatchAnalysis(
                match_score=82,
                recommendation="good_match",
                strong_matches=["Python", "FastAPI"],
                partial_matches=["PostgreSQL"],
                missing_skills=["Docker"],
                risk_points=["Limited cloud experience"],
                reasoning_summary=(
                    "The candidate matches most core requirements."
                ),
            )
        ),
    )

    response = client.post(
        f"/tracked-vacancies/{tracked_vacancy_id}/match-analysis",
        headers=auth_headers,
    )

    assert response.status_code == 201

    return response.json()


def prepare_generated_content_data(
    client,
    monkeypatch,
    *,
    with_match_analysis: bool = False,
) -> dict:
    """Create all persisted data required for generated content tests."""

    user_data = create_test_user(client)
    auth_headers = get_auth_headers(client, user_data)
    profile = create_test_profile(client, auth_headers, user_data)
    resume = create_test_resume(client, auth_headers, monkeypatch)
    vacancy = create_test_vacancy(client, auth_headers, monkeypatch)
    tracked_vacancy = create_test_tracked_vacancy(
        client,
        auth_headers,
        resume["id"],
        vacancy["id"],
    )

    match_analysis = None
    if with_match_analysis:
        match_analysis = create_test_match_analysis(
            client,
            auth_headers,
            tracked_vacancy["id"],
            vacancy["id"],
            monkeypatch,
        )

    return {
        "auth_headers": auth_headers,
        "profile": profile,
        "resume": resume,
        "vacancy": vacancy,
        "tracked_vacancy": tracked_vacancy,
        "match_analysis": match_analysis,
    }


def build_generation_request() -> dict:
    """Build a valid cover letter generation request."""

    return {
        "content_type": "cover_letter",
        "language": "en",
        "tone": "professional",
        "extra_instructions": "Keep it concise.",
    }


def test_generate_cover_letter(client, monkeypatch):
    test_data = prepare_generated_content_data(client, monkeypatch)

    async def mock_generate_content_chain(
        content_type,
        resume_text,
        vacancy_text,
        match_analysis_text,
        language,
        tone,
        extra_instructions,
    ):
        assert content_type == "cover_letter"
        assert resume_text == VALID_RESUME_TEXT
        assert vacancy_text == VALID_VACANCY_TEXT
        assert match_analysis_text is None
        assert language == "en"
        assert tone == "professional"
        assert extra_instructions == "Keep it concise."

        return ParsedGeneratedContent(
            generated_text=GENERATED_COVER_LETTER,
        )

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        mock_generate_content_chain,
    )

    response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )

    assert response.status_code == 201

    response_data = response.json()
    prompt_context = response_data["prompt_context"]

    assert response_data["tracked_vacancy_id"] == (
        test_data["tracked_vacancy"]["id"]
    )
    assert response_data["content_type"] == "cover_letter"
    assert response_data["generated_text"] == GENERATED_COVER_LETTER
    assert response_data["ai_model"] is not None
    assert response_data["prompt_version"] == GENERATED_CONTENT_PROMPT_VERSION

    assert prompt_context["content_type"] == "cover_letter"
    assert prompt_context["language"] == "en"
    assert prompt_context["tone"] == "professional"
    assert prompt_context["extra_instructions"] == "Keep it concise."
    assert prompt_context["resume_document_id"] == test_data["resume"]["id"]
    assert prompt_context["vacancy_id"] == test_data["vacancy"]["id"]
    assert prompt_context["match_analysis_id"] is None


def test_generate_cover_letter_uses_match_analysis(
    client,
    monkeypatch,
):
    test_data = prepare_generated_content_data(
        client,
        monkeypatch,
        with_match_analysis=True,
    )

    async def mock_generate_content_chain(**kwargs):
        match_analysis_text = kwargs["match_analysis_text"]

        assert "Match score: 82" in match_analysis_text
        assert "Recommendation: good_match" in match_analysis_text
        assert "Strong matches: Python, FastAPI" in match_analysis_text
        assert "Missing skills: Docker" in match_analysis_text

        return ParsedGeneratedContent(
            generated_text=GENERATED_COVER_LETTER,
        )

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        mock_generate_content_chain,
    )

    response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )

    assert response.status_code == 201
    assert response.json()["prompt_context"]["match_analysis_id"] == (
        test_data["match_analysis"]["id"]
    )


def test_get_generated_content_history_and_item(
    client,
    monkeypatch,
):
    test_data = prepare_generated_content_data(client, monkeypatch)
    generation_mock = AsyncMock(
        side_effect=[
            ParsedGeneratedContent(generated_text="First cover letter."),
            ParsedGeneratedContent(generated_text="Second cover letter."),
        ]
    )

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        generation_mock,
    )

    generation_path = (
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate"
    )

    first_response = client.post(
        generation_path,
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )
    second_response = client.post(
        generation_path,
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_content = first_response.json()
    second_content = second_response.json()

    history_response = client.get(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content",
        headers=test_data["auth_headers"],
    )

    assert history_response.status_code == 200
    assert {
        item["id"]
        for item in history_response.json()
    } == {
        first_content["id"],
        second_content["id"],
    }

    item_response = client.get(
        f"/tracked-vacancies/generated-content/{first_content['id']}",
        headers=test_data["auth_headers"],
    )

    assert item_response.status_code == 200
    assert item_response.json() == first_content


def test_update_generated_content(client, monkeypatch):
    test_data = prepare_generated_content_data(client, monkeypatch)

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        AsyncMock(
            return_value=ParsedGeneratedContent(
                generated_text=GENERATED_COVER_LETTER,
            )
        ),
    )

    create_response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )

    assert create_response.status_code == 201

    created_content = create_response.json()
    update_response = client.patch(
        f"/tracked-vacancies/generated-content/{created_content['id']}",
        headers=test_data["auth_headers"],
        json={
            "generated_text": "Manually edited cover letter.",
        },
    )

    assert update_response.status_code == 200

    updated_content = update_response.json()

    assert updated_content["id"] == created_content["id"]
    assert updated_content["tracked_vacancy_id"] == (
        created_content["tracked_vacancy_id"]
    )
    assert updated_content["generated_text"] == (
        "Manually edited cover letter."
    )
    assert updated_content["ai_model"] == created_content["ai_model"]
    assert updated_content["prompt_version"] == created_content["prompt_version"]

    get_response = client.get(
        f"/tracked-vacancies/generated-content/{created_content['id']}",
        headers=test_data["auth_headers"],
    )

    assert get_response.status_code == 200
    assert get_response.json()["generated_text"] == (
        "Manually edited cover letter."
    )


def test_other_user_cannot_access_generated_content(
    client,
    monkeypatch,
):
    test_data = prepare_generated_content_data(client, monkeypatch)
    generation_mock = AsyncMock(
        return_value=ParsedGeneratedContent(
            generated_text=GENERATED_COVER_LETTER,
        )
    )

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        generation_mock,
    )

    create_response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=test_data["auth_headers"],
        json=build_generation_request(),
    )

    assert create_response.status_code == 201

    generated_content = create_response.json()
    other_user = create_test_user(client)
    other_user_headers = get_auth_headers(client, other_user)

    generate_response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=other_user_headers,
        json=build_generation_request(),
    )
    list_response = client.get(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content",
        headers=other_user_headers,
    )
    get_response = client.get(
        f"/tracked-vacancies/generated-content/{generated_content['id']}",
        headers=other_user_headers,
    )
    patch_response = client.patch(
        f"/tracked-vacancies/generated-content/{generated_content['id']}",
        headers=other_user_headers,
        json={
            "generated_text": "Unauthorized edit.",
        },
    )

    assert generate_response.status_code == 404
    assert generate_response.json()["detail"] == "Tracked vacancy not found."

    assert list_response.status_code == 404
    assert list_response.json()["detail"] == "Tracked vacancy not found."

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Generated content not found."

    assert patch_response.status_code == 404
    assert patch_response.json()["detail"] == "Generated content not found."
    assert generation_mock.await_count == 1


def test_generate_content_rejects_unsupported_type(
    client,
    monkeypatch,
):
    test_data = prepare_generated_content_data(client, monkeypatch)
    generation_mock = AsyncMock()

    monkeypatch.setattr(
        "app.services.generated_content_service.generate_content_chain",
        generation_mock,
    )

    response = client.post(
        "/tracked-vacancies/"
        f"{test_data['tracked_vacancy']['id']}"
        "/generated-content/generate",
        headers=test_data["auth_headers"],
        json={
            "content_type": "linkedin_post",
            "language": "en",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Unsupported generated content type: linkedin_post"
    )
    generation_mock.assert_not_awaited()
