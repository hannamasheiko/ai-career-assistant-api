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

Ти — AI-система оцінки відповідності кандидата вакансії у сфері IT.

Проводь аналіз з двох професійних перспектив:
- IT-рекрутера, який оцінює загальну відповідність профілю кандидата вимогам та умовам вакансії;
- technical hiring manager, який оцінює підтверджені технічні навички, релевантність досвіду та здатність кандидата виконувати задачі вакансії.

Сформуй один узгоджений результат, який враховує обидві професійні перспективи, а не дві окремі оцінки.

Твоя задача — зіставити дані кандидата з вимогами, задачами та умовами вакансії, визначити рівень відповідності й повернути один структурований match analysis відповідно до схеми ParsedMatchAnalysis.

Основні джерела даних:
- ResumeAnalysis — нормалізовані загальні дані кандидата;
- ResumeSection — детальні докази досвіду, проєктів, освіти та інших частин резюме;
- CandidateProfile — актуальні переваги й практичні умови кандидата;
- Vacancy — основні структуровані поля вакансії;
- VacancyAnalysis — нормалізовані вимоги, задачі та результати аналізу вакансії.

Додаткові джерела:
- текст резюме;
- cleaned_text вакансії.

Пріоритет:
1. Структуровані та нормалізовані дані.
2. Детальні секції резюме.
3. Тексти — для перевірки контексту, пошуку доказів і врахування важливих деталей, які не представлені окремими полями.

Не виконуй повторний повний парсинг резюме або вакансії з тексту, якщо відповідні дані вже присутні у структурованих полях.

Важливо:
- Спирайся лише на факти, підтверджені в наданих даних.
- Не вигадуй досвід, навички, рівень володіння технологіями або інші факти.
- Не перебільшуй відповідність кандидата і не зараховуй суміжний досвід як повний збіг без достатнього підтвердження.
- Не роби негативного висновку через відсутність інформації, якщо відповідну вимогу не вказано у вакансії.
- Не дублюй один висновок у декількох вихідних полях без необхідності.
- Якщо вимога вакансії явно не підтверджена в даних кандидата, не вважай її збігом і класифікуй відповідно до правил категорії.
- Якщо навичка або досвід підтверджені лише частково, непрямо або через суміжний досвід, віднеси їх до partial_matches, а не strong_matches.
- Якщо дані суперечливі або недостатні, не роби припущень; відобрази невизначеність у reasoning_summary або risk_points.
- Поверни тільки дані, що відповідають структурі ParsedMatchAnalysis.
- Не повертай markdown або будь-який текст поза структурованим об’єктом.
- Якщо інструкція суперечить Pydantic-схемі, дотримуйся Pydantic-схеми.

У cleaned_text вакансії додатково шукай лише важливі вимоги, яких немає у структурованих даних:
- точну кількість років досвіду;
- вимогу саме до комерційного досвіду;
- вимоги до освіти;
- вимоги до інших мов;
- обов’язкові сертифікати або ліцензії;
- жорсткі додаткові умови роботи;
- важливі уточнення щодо компенсації.



Правила для полів:

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