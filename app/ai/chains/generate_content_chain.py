from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedGeneratedContent
from app.services.openai_cost_tracker import print_openai_usage


async def generate_content_chain(
    content_type: str,
    resume_text: str,
    vacancy_text: str,
    match_analysis_text: str | None,
    language: str,
    tone: str | None,
    extra_instructions: str | None,
) -> ParsedGeneratedContent:
    """Generate AI content for a tracked vacancy."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    if content_type != "cover_letter":
        raise ValueError(f"Unsupported generated content type: {content_type}")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ти — AI career assistant, який допомагає кандидату підготувати текст для відгуку на вакансію.

Зараз підтримується тільки один тип generated content: cover_letter.

Твоя задача — згенерувати супровідний лист для конкретної вакансії на основі:
- резюме кандидата;
- тексту вакансії;
- match analysis, якщо він є;
- додаткових інструкцій користувача.

Важливо:
- Поверни тільки дані, які відповідають структурі ParsedGeneratedContent.
- Не вигадуй досвід, навички, компанії або факти, яких немає в резюме.
- Не перебільшуй відповідність кандидата.
- Не згадуй явно слабкі сторони, missing skills або risk points, якщо користувач не просить.
- Використовуй сильні збіги як основу листа.
- Якщо є partial matches, формулюй їх обережно.
- Текст має бути природним, професійним і придатним для відправки.
- Не використовуй markdown.
- Не додавай тему листа, якщо користувач не просить.
- Не повертай текст поза структурованим обʼєктом.
- Якщо інструкція суперечить Pydantic-схемі, дотримуйся Pydantic-схеми.

Правила для cover_letter:
- Мова відповіді має відповідати полю language.
- Тон має відповідати полю tone.
- Не роби лист занадто довгим.
- Оптимальна довжина: 3-5 коротких абзаців.
- Почни з короткого звернення або нейтрального вступу.
- Поясни, чому кандидат зацікавлений у вакансії.
- Покажи 2-4 релевантні сильні сторони кандидата.
- Заверши готовністю обговорити досвід на співбесіді.
""",
            ),
            (
                "user",
                """
Тип контенту:
{content_type}

Мова:
{language}

Тон:
{tone}

Додаткові інструкції користувача:
{extra_instructions}

Резюме кандидата:
{resume_text}

Вакансія:
{vacancy_text}

Match analysis:
{match_analysis_text}
""",
            ),
        ]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )

    structured_llm = llm.with_structured_output(
        ParsedGeneratedContent,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "content_type": content_type,
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
            "match_analysis_text": match_analysis_text or "Match analysis is not available.",
            "language": language,
            "tone": tone or "professional",
            "extra_instructions": extra_instructions or "No extra instructions.",
        }
    )

    parsed_generated_content = result["parsed"]
    raw_response = result["raw"]

    if parsed_generated_content is None:
        raise RuntimeError("Failed to generate structured content")

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

    return parsed_generated_content

