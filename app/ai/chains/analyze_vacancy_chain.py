from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedVacancyAnalysis
from app.services.openai_cost_tracker import print_openai_usage


VACANCY_ANALYSIS_PROMPT_VERSION = "vacancy_analysis_v1"


async def analyze_vacancy_chain(vacancy_text: str) -> ParsedVacancyAnalysis:
    """Analyze vacancy text into structured AI-generated vacancy analysis."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ти — AI-сервіс для детального аналізу вакансій.

Твоя задача — проаналізувати текст вакансії як окремий job posting.

Важливо:
- Аналізуй тільки саму вакансію.
- Не порівнюй вакансію з конкретним кандидатом.
- Не створюй match score.
- Не створюй cover letter.
- Не створюй tracked vacancy.
- Не вигадуй вимоги, яких немає в тексті.
- Якщо інформацію неможливо визначити — поверни null або порожній список.
- Поверни тільки дані, які відповідають структурі ParsedVacancyAnalysis.
- Не повертай markdown.
- Не повертай пояснення поза структурованим обʼєктом.

Правила для полів:

experience_level:
- Визнач рівень вакансії: internship, trainee, junior, junior+, middle, senior, lead, unknown.
- Якщо рівень явно не вказаний, але його можна обережно визначити з вимог — визнач.
- Якщо визначити неможливо — "unknown".

english_level:
- Визнач рівень англійської: none, basic, pre-intermediate, intermediate, upper-intermediate, advanced, fluent, unknown.
- Якщо англійська не згадується — "unknown".

required_skills:
- Обовʼязкові hard skills, technologies, frameworks, databases, tools.
- Включай тільки те, що виглядає як must-have.

optional_skills:
- Nice-to-have skills.
- Включай тільки те, що явно або контекстно подано як бажане/плюс.

responsibilities:
- Основні обовʼязки на посаді.
- Формулюй коротко і структуровано.

red_flags:
- Потенційні ризики вакансії.
- Наприклад: нечіткі вимоги, завищені вимоги для junior, відсутність зарплати, багато неповʼязаних ролей в одній вакансії, сумнівні формулювання.
- Не вигадуй red flags, якщо їх немає.

green_flags:
- Позитивні ознаки вакансії.
- Наприклад: чіткий стек, адекватний рівень, навчання, менторство, прозорий процес, релевантний backend stack, remote.

summary:
- Коротко поясни, що це за вакансія по суті.
- 3–6 речень.
- Без порівняння з кандидатом.

recommendation:
- Оціни вакансію як job posting.
- Використовуй одне з:
  - "strong_opportunity"
  - "worth_reviewing"
  - "questionable"
  - "not_recommended"
  - "insufficient_information"
""",
            ),
            (
                "user",
                """
Проаналізуй цю вакансію і поверни структурований AI analysis.

Текст вакансії:
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
        ParsedVacancyAnalysis,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "vacancy_text": vacancy_text,
        }
    )

    parsed_analysis = result["parsed"]
    raw_response = result["raw"]

    if parsed_analysis is None:
        raise RuntimeError("Failed to analyze vacancy into structured output")

    usage_metadata = getattr(raw_response, "usage_metadata", None)

    if usage_metadata:
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        total_tokens = usage_metadata.get("total_tokens", 0)

        print_openai_usage(
            model=settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    return parsed_analysis

