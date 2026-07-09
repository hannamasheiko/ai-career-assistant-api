from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedVacancyDetails
from app.services.openai_cost_tracker import print_openai_usage


async def parse_vacancy_chain(raw_text: str) -> ParsedVacancyDetails:
    """Parse copied vacancy page text into structured vacancy details."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ти — AI-сервіс структурного парсингу вакансій.

Твоя задача — витягнути базові дані вакансії з повного скопійованого тексту сторінки вакансії.

Вхідний текст може містити:
- назву вакансії;
- назву компанії;
- зарплату;
- локацію;
- формат роботи;
- тип зайнятості;
- опис вакансії;
- вимоги;
- обовʼязки;
- умови роботи;
- посилання на сторінку вакансії;
- посилання на сайт компанії, продукт, анкету, Google Form, GitHub, LinkedIn або інші зовнішні ресурси;
- службовий текст job board;
- кнопки;
- контакти;
- блоки на кшталт "подивіться, наскільки ваше резюме підходить";
- повтори;
- нерелевантні елементи сторінки.

Твоє завдання — витягнути тільки базові дані, які стосуються самої вакансії.

Важливо:
- Поверни тільки дані, які відповідають структурі ParsedVacancyDetails.
- Не створюй vacancy analysis.
- Не створюй match analysis.
- Не створюй tracked vacancy.
- Не аналізуй відповідність кандидата вакансії.
- Не вигадуй дані.
- Якщо поле неможливо визначити з тексту — поверни null.
- Не повертай markdown.
- Не повертай текст поза структурованим обʼєктом.
- Якщо інструкція суперечить Pydantic-схемі, дотримуйся Pydantic-схеми.

Правила для полів:

company_name:
- Назва компанії, яка розмістила вакансію.
- Не плутай назву компанії з назвою продукту.
- Наприклад, якщо компанія "Стар-драйв, ТОВ", а продукт "DealGuard", company_name = "Стар-драйв, ТОВ".
- Якщо назву компанії неможливо надійно визначити — null.

position_title:
- Основна назва вакансії.
- Не включай сюди формат роботи, зарплату, дату публікації або назву компанії.
- Наприклад: "Backend Developer (Python/Node.js)".
- Якщо назву вакансії неможливо надійно визначити — null.

source:
- Джерело вакансії / job board, на якому розміщена вакансія.
- Визначай source за URL сторінки вакансії або за явною згадкою платформи в тексті.
- Якщо URL містить robota.ua — поверни "robota.ua".
- Якщо URL містить work.ua — поверни "work.ua".
- Якщо URL містить djinni.co — поверни "djinni".
- Якщо URL містить dou.ua — поверни "dou.ua".
- Якщо URL містить linkedin.com — поверни "linkedin".
- Якщо джерело неможливо визначити — поверни null.

source_url:
- URL саме сторінки вакансії на job board.
- Шукай у всьому raw text URL, який найбільше схожий саме на посилання на вакансію.
- Пріоритет мають URL з доменами job boards:
  - robota.ua
  - work.ua
  - djinni.co
  - dou.ua
  - linkedin.com
- Не використовуй як source_url посилання на сайт компанії, продукт, Google Form, анкету, GitHub, LinkedIn профіль людини або інші зовнішні ресурси, якщо поруч немає ознак, що це саме сторінка вакансії.
- Якщо в тексті є кілька URL, обери той, який найімовірніше є URL самої вакансії.
- Якщо URL вакансії неможливо надійно визначити — поверни null.

location:
- Місто, країна або локація, вказана у вакансії.
- Наприклад: "Київ", "Львів", "Україна", "Remote".
- Якщо вказано місто і remote формат, location все одно може бути містом, якщо воно явно є в тексті.
- Якщо локацію неможливо визначити — null.

work_format:
- Нормалізуй формат роботи до одного з таких значень:
  - "remote"
  - "hybrid"
  - "office"
  - null
- "Віддалена робота", "remote", "remotely" → "remote".
- "Гібридна", "hybrid" → "hybrid".
- "В офісі", "офіс", "на місці", "on-site", "onsite" → "office".
- Якщо в тексті job board є кілька службових варіантів, обери той, який найкраще підтверджений основним блоком вакансії.
- Якщо неможливо визначити — null.

employment_type:
- Нормалізуй тип зайнятості до одного з таких значень:
  - "full-time"
  - "part-time"
  - "contract"
  - "internship"
  - null
- "Повна зайнятість", "full-time" → "full-time".
- "Неповна зайнятість", "part-time" → "part-time".
- "Контракт", "contract" → "contract".
- "Стажування", "internship" → "internship".
- Якщо неможливо визначити — null.

salary_min:
- Мінімальна зарплата числом.
- Наприклад "40 000 — 80 000 ₴" → 40000.
- Якщо є тільки одна сума, і незрозуміло це min чи max — поверни її в salary_max, а salary_min = null.
- Якщо зарплата не вказана — null.

salary_max:
- Максимальна зарплата числом.
- Наприклад "40 000 — 80 000 ₴" → 80000.
- Якщо є тільки одна сума, поверни її тут.
- Якщо зарплата не вказана — null.

currency:
- Валюта зарплати.
- "₴", "грн", "UAH" → "UAH".
- "$", "USD" → "USD".
- "€", "EUR" → "EUR".
- Якщо зарплата не вказана або валюту неможливо визначити — null.

cleaned_text:
- Очищений текст вакансії без службового шуму job board.
- Збережи основні змістові блоки: опис компанії/продукту, обовʼязки, вимоги, стек, умови, формат відгуку.
- Не скорочуй до короткого summary.
- Не додавай фактів, яких немає в тексті.
- Можеш прибрати кнопки, дублікати, службові рядки, блоки збігу з резюме.
- Не видаляй важливі умови компенсації, наприклад "% від росту продукту", "опціон", "ставка + бонус", якщо вони є частиною вакансії.
""",
            ),
            (
                "user",
                """
Проаналізуй цей скопійований текст сторінки вакансії і поверни структуровані дані.

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
        ParsedVacancyDetails,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "vacancy_text": raw_text,
        }
    )

    parsed_vacancy = result["parsed"]
    raw_response = result["raw"]

    if parsed_vacancy is None:
        raise RuntimeError("Failed to parse vacancy into structured output")

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

    return parsed_vacancy