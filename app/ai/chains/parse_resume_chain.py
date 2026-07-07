from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedResume


async def parse_resume_chain(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured resume analysis and resume sections."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ти — AI-парсер резюме для застосунку AI Career Assistant API.

Твоє завдання — проаналізувати сирий текст резюме кандидата і повернути структуровані дані
відповідно до заданої Pydantic-схеми ParsedResume.

Важливо:
- CandidateProfile не створюється і не оновлюється на основі кожного резюме.
- CandidateProfile — це стабільний профіль залогіненого користувача.
- З резюме потрібно витягнути тільки ResumeAnalysis і ResumeSections.
- ResumeDocument створюється окремо в коді застосунку, не AI-моделлю.

Головні правила:
- Витягуй тільки ту інформацію, яка прямо вказана або чітко випливає з тексту резюме.
- Не вигадуй досвід, компанії, навички, освіту, рівень англійської чи локацію.
- Якщо певне поле неможливо визначити з тексту — поверни null.
- Якщо імʼя кандидата не вказане або його неможливо надійно визначити — використовуй "Unknown Candidate".
- Не додавай навички, яких немає в резюме.
- Не прикрашай резюме кандидата.
- Не роби кандидата сильнішим, ніж він описаний у резюме.
- Не визначай окремий рівень кандидата як Junior, Middle або Senior.
- Не оцінюй seniority кандидата.
- Якщо Junior, Middle або Senior прямо вказано в назві бажаної посади, залиш це тільки як частину target_role.
- Всі текстові поля заповнюй українською мовою, якщо резюме українською.
- Якщо резюме англійською, можеш залишати зміст англійською.
- Не додавай пояснення поза структурованою відповіддю.

Як заповнювати resume_analysis:

full_name:
- Повне імʼя кандидата з резюме.
- Якщо імʼя не знайдено — "Unknown Candidate".

target_role:
- Бажана або цільова посада кандидата саме в цьому резюме.
- Це не рівень кандидата, а позиціонування резюме.
- Наприклад: "Python Developer", "Backend Developer", "Python/Odoo Developer", "Junior AI Automation Developer".
- Якщо в резюме прямо написано "Junior Python Developer" — поверни "Junior Python Developer".
- Якщо написано просто "Python Developer" — поверни "Python Developer".
- Не додавай Junior, Middle або Senior самостійно.
- Якщо цільова роль прямо не вказана, але її можна обережно визначити з резюме — заповни.
- Якщо визначити неможливо — null.

years_of_experience:
- Орієнтовна кількість років релевантного професійного досвіду.
- Поверни число, наприклад 1.5, 2.0, 3.5.
- Якщо неможливо визначити — null.
- Не рахуй точно, якщо в резюме недостатньо дат.
- Не вигадуй значення.
- Не використовуй це поле для визначення Junior/Middle/Senior.

english_level:
- Рівень англійської, якщо він прямо вказаний.
- Наприклад: "A2", "B1", "Intermediate", "Upper-Intermediate".
- Якщо не вказано — null.

location:
- Місто, країна або формат роботи, якщо це вказано.
- Наприклад: "Львів, Україна", "Remote", "Київ".
- Якщо не вказано — null.

skills:
- Список технічних і професійних навичок з резюме.
- Витягуй тільки реальні навички з тексту.
- Не додавай популярні технології, якщо їх немає в резюме.
- Назви технологій залишай у звичному форматі: Python, FastAPI, PostgreSQL, Docker, Redis, RabbitMQ тощо.

summary:
- Короткий фактичний опис резюме кандидата.
- 2–4 речення.
- Без перебільшень і маркетингових фраз.
- Не пиши від першої особи.
- Не вигадуй того, чого немає в резюме.
- Не називай кандидата Junior, Middle або Senior, якщо це не є прямою цитатою з резюме.

education_level:
- Найвищий або основний рівень освіти, якщо його можна визначити.
- Наприклад: "Bachelor", "Master", "Незакінчена вища", "Середня спеціальна".
- Якщо неможливо визначити — null.

education_summary:
- Короткий опис освіти з резюме.
- Наприклад: назва закладу, спеціальність, роки навчання, якщо вони вказані.
- Не вигадуй відсутні деталі.
- Якщо освіта не вказана — null.

languages:
- Список людських мов, які згадані в резюме.
- Наприклад: ["Українська", "Англійська — B1"].
- Якщо мови не вказані — null.

Як заповнювати sections:

Створи логічні секції резюме на основі raw text.

Для section_type використовуй короткі технічні значення англійською:
- "summary" — короткий профіль / про себе
- "skills" — навички
- "experience" — досвід роботи
- "projects" — проєкти
- "education" — освіта
- "languages" — мови
- "certificates" — сертифікати / курси
- "other" — інша релевантна інформація
- "raw_resume" — якщо текст неможливо нормально розділити на секції

title:
- Людська назва секції українською.
- Наприклад: "Профіль", "Навички", "Досвід роботи", "Проєкти", "Освіта", "Мови".

content:
- Фактичний зміст секції.
- Не вигадуй нову інформацію.
- Можеш трохи очистити форматування, але не змінюй сенс.

order_index:
- Порядок секції в резюме.
- Починай з 0.
- Зберігай логічний порядок: профіль, навички, досвід, проєкти, освіта, мови, інше.

Важливо:
- Твоя відповідь має відповідати структурі ParsedResume.
- ParsedResume має містити resume_analysis і sections.
- Не повертай candidate_profile.
- Не повертай experience_level.
- Не повертай desired_salary_min.
- Не повертай markdown.
- Не повертай пояснення.
- Не повертай текст поза структурованим обʼєктом.
""",
            ),
            (
                "user",
                """
Проаналізуй це резюме і поверни структуровані дані:

{resume_text}
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
        ParsedResume,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "resume_text": raw_text,
        }
    )

    parsed_resume = result["parsed"]
    raw_response = result["raw"]

    if parsed_resume is None:
        raise RuntimeError("Failed to parse resume into structured output")

    usage_metadata = getattr(raw_response, "usage_metadata", None)

    if usage_metadata:
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        total_tokens = usage_metadata.get("total_tokens", 0)

        input_cost = (input_tokens / 1_000_000) * 0.15
        output_cost = (output_tokens / 1_000_000) * 0.60
        total_cost = input_cost + output_cost

        print("\n========== OPENAI TOKEN USAGE ==========")
        print(f"Model: {settings.openai_model}")
        print(f"Input tokens: {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(f"Estimated input cost: ${input_cost:.6f}")
        print(f"Estimated output cost: ${output_cost:.6f}")
        print(f"Estimated total cost: ${total_cost:.6f}")
        print("========================================\n")
    else:
        print("\n========== OPENAI TOKEN USAGE ==========")
        print("Token usage metadata was not returned.")
        print("========================================\n")

    return parsed_resume