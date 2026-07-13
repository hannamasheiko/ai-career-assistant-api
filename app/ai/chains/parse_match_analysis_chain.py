import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.ai.context_builders.match_analysis_context import (
    build_resume_analysis_data,
    build_resume_sections_data,
    build_vacancy_analysis_data,
    build_vacancy_data,
)
from app.core.config import settings
from app.models.resume import ResumeSection
from app.models.resume_analysis import ResumeAnalysis
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.schemas.ai_outputs import ParsedMatchAnalysis
from app.services.openai_cost_tracker import print_openai_usage


async def parse_match_analysis_chain(
    resume_analysis: ResumeAnalysis,
    resume_sections: list[ResumeSection],
    vacancy: Vacancy,
    vacancy_analysis: VacancyAnalysis,
    resume_text: str,
    vacancy_text: str,
) -> ParsedMatchAnalysis:
    """Analyze how well a resume matches a vacancy."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    resume_analysis_json = json.dumps(
        build_resume_analysis_data(resume_analysis),
        ensure_ascii=False,
        indent=2,
    )

    resume_sections_json = json.dumps(
        build_resume_sections_data(resume_sections),
        ensure_ascii=False,
        indent=2,
    )
    vacancy_json = json.dumps(
        build_vacancy_data(vacancy),
        ensure_ascii=False,
        indent=2,
    )
    vacancy_analysis_json = json.dumps(
        build_vacancy_analysis_data(vacancy_analysis),
        ensure_ascii=False,
        indent=2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ти — AI career assistant, який аналізує відповідність резюме конкретній вакансії.

Твоя задача — порівняти резюме кандидата з текстом вакансії і повернути структурований match analysis.

Важливо:
- Поверни тільки дані, які відповідають структурі ParsedMatchAnalysis.
- Не вигадуй досвід, навички або факти, яких немає в резюме.
- Не перебільшуй відповідність кандидата.
- Якщо вимога є у вакансії, але її немає в резюме — вкажи це в missing_skills або risk_points.
- Якщо навичка згадана в резюме, але слабко або непрямо — це partial_match, а не strong_match.
- Не повертай markdown.
- Не повертай текст поза структурованим обʼєктом.
- Якщо інструкція суперечить Pydantic-схемі, дотримуйся Pydantic-схеми.

Правила для полів:

match_score:
- Число від 0 до 100.
- 90-100: дуже сильна відповідність.
- 75-89: хороша відповідність.
- 55-74: часткова відповідність.
- 30-54: слабка відповідність.
- 0-29: майже не підходить.
- Оцінюй не тільки за кількістю збігів, а й за важливістю вимог.

recommendation:
- Поверни одне коротке значення:
  - "strong_match"
  - "good_match"
  - "partial_match"
  - "weak_match"
  - "not_recommended"

strong_matches:
- Список сильних збігів між резюме і вакансією.
- Наприклад: "Python", "FastAPI", "PostgreSQL", "REST API", "commercial backend experience".
- Додавай тільки те, що справді підтверджено в резюме.

partial_matches:
- Список часткових збігів.
- Наприклад: вакансія вимагає SaaS, а кандидат має backend/API досвід, але не явний SaaS.
- Або вакансія вимагає Telegram Bot API, а кандидат має Python API integrations, але не Telegram Bot API.

missing_skills:
- Список важливих вимог вакансії, яких немає в резюме.
- Не додавай дрібниці, які не впливають на рішення.
- Не додавай те, що явно є в резюме.

risk_points:
- Ризики для кандидата щодо цієї вакансії.
- Наприклад: недостатній комерційний досвід, відсутність конкретного фреймворку, слабкий збіг з доменом, нестандартна компенсація.
- Ризики мають бути повʼязані саме з match між резюме і вакансією.

reasoning_summary:
- Коротке пояснення українською мовою.
- 3-6 речень.
- Поясни, чому такий score і recommendation.
""",
            ),
            (
                "user",
                """
Резюме кандидата:
{resume_text}

Вакансія:
{vacancy_text}
""",
            ),
        ]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(
        ParsedMatchAnalysis,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
        }
    )

    parsed_match_analysis = result["parsed"]
    raw_response = result["raw"]

    if parsed_match_analysis is None:
        raise RuntimeError(
            "Failed to parse match analysis into structured output"
        )

    usage_metadata = getattr(
        raw_response,
        "usage_metadata",
        None,
    )

    if usage_metadata:
        input_tokens = usage_metadata.get(
            "input_tokens",
            0,
        )
        output_tokens = usage_metadata.get(
            "output_tokens",
            0,
        )
        total_tokens = usage_metadata.get(
            "total_tokens",
            0,
        )

        print_openai_usage(
            model=settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    return parsed_match_analysis