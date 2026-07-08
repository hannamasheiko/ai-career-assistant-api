from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedResume

from app.services.openai_cost_tracker import print_openai_usage


async def parse_resume_chain(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured resume analysis and resume sections."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """

Ти — AI-сервіс структурного парсингу резюме.
Твоя задача — extraction, normalization and sectioning: витягнути факти, безпечно нормалізувати значення і розкласти текст на логічні секції.
Ти не оцінюєш кандидата і не робиш висновків про його seniority.

Важливо:
- Поверни тільки дані, які відповідають структурі ParsedResume: resume_analysis, sections і work_experience_periods.
- Не створюй і не оновлюй профіль кандидата.
- Не повертай дані, яких немає у схемі.
- Не додавай пояснення поза структурованою відповіддю.
- Якщо інструкція суперечить Pydantic-схемі, дотримуйся Pydantic-схеми.
- Якщо для list-поля немає даних — поверни null.
- Не повертай markdown.
- Не повертай текст поза структурованим обʼєктом.

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
- Якщо резюме змішане українською та англійською, зберігай назви технологій англійською, а описові поля формуй мовою, яка переважає в резюме.

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
- Не розраховуй years_of_experience самостійно.
- Якщо поле years_of_experience є в resume_analysis, поверни null.
- Фінальне значення years_of_experience буде пораховане backend-кодом на основі work_experience_periods.
- Не використовуй це поле для визначення Junior/Middle/Senior.

english_level:
- Рівень англійської, якщо він прямо вказаний або очевидно позначений у резюме.
- Нормалізуй до короткого зрозумілого формату.
- Приклади:
  "Intermediate" → "B1 / Intermediate"
  "B1" → "B1"
  "Upper-Intermediate" → "B2 / Upper-Intermediate"
  "Pre-Intermediate" → "A2 / Pre-Intermediate"
  "Elementary" → "A1 / Elementary"
  "Advanced" → "C1 / Advanced"
  "Fluent" → "C1 / Fluent"
  "середній" → "B1 / Intermediate"
  "вище середнього" → "B2 / Upper-Intermediate"
  "базовий" → "A1-A2 / Basic"
- Якщо вказано просто "English" без рівня — поверни "English, level not specified".
- Якщо вказано кілька формулювань, наприклад "English — Intermediate (B1)", поверни "B1 / Intermediate".
- Якщо англійська не згадана — null.
- Не вигадуй рівень, якщо в резюме немає підстав.

location:
- Локація кандидата або бажаний формат роботи, якщо це прямо вказано в контактному блоці чи шапці резюме.
- Наприклад: "Львів, Україна", "Київ", "Remote".
- Якщо є і місто, і формат роботи — поверни коротко обидва, наприклад "Львів, Україна / Remote".
- Якщо не вказано — null.

skills:
- Список технічних і професійних навичок з резюме.
- Витягуй тільки реальні навички з тексту.
- Не додавай популярні технології, якщо їх немає в резюме.
- Назви технологій залишай у звичному форматі: Python, FastAPI, PostgreSQL, Docker, Redis, RabbitMQ тощо.
- Не включай людські мови в skills.
- Не включай soft skills у skills.
- Якщо soft skills є окремо в резюме, залиш їх у sections, але не додавай у resume_analysis.skills.
- Дедуплікуй навички: "JS" і "JavaScript" краще повернути як "JavaScript", якщо це безпечно.
- Не розбивай складені технології неправильно: "HTML/CSS/JavaScript" можна розділити на "HTML", "CSS", "JavaScript".

summary:
- Якщо в резюме є окремий розділ Summary / Profile / About / Про себе / Профіль — використовуй його як основу.
- Не переписуй його з нуля і не додавай нові факти.
- Якщо summary адекватного розміру — збережи його зміст максимально повно.
- Якщо summary дуже довгий, більше 10 речень, або містить повтори — скороти й очисти його, але не додавай нових фактів і не змінюй сенс.
- Якщо summary у резюме відсутній — сформуй короткий фактичний summary на основі всього резюме.
- У такому випадку 4–6 речень.
- Без перебільшень, маркетингових фраз і оцінок.
- Не називай кандидата Junior, Middle або Senior, якщо це не є прямою цитатою з резюме.

education_level:
- Найвищий визначений рівень освіти.
- Використовуй один із форматів:
  "Higher education — Master"
  "Higher education — Bachelor"
  "Higher education — PhD"
  "Incomplete higher education"
  "Higher education"
  "Vocational / secondary specialized education"
  "Secondary education"
  null
- Якщо є магістр — поверни "Higher education — Master".
- Якщо є бакалавр і немає магістра — "Higher education — Bachelor".
- Якщо вказано просто "вища освіта" без ступеня — "Higher education".
- Якщо неможливо визначити — null.

education_summary:
- Короткий опис освіти з резюме.
- Наприклад: назва закладу, спеціальність, роки навчання, якщо вони вказані.
- Не вигадуй відсутні деталі.
- Якщо освіта не вказана — null.

languages:
- Список людських мов, згаданих у резюме, крім англійської.
- Не включай English / Англійську в це поле, бо для неї є окреме поле english_level.
- Якщо для мови вказаний рівень — збережи його.
- Якщо рівень не вказаний — поверни тільки назву мови.
- Не вигадуй рівень мови, якщо він не вказаний.
- Приклади:
  "Українська" → "Українська"
  "Українська — рідна" → "Українська — рідна"
  "Українська — вільно" → "Українська — вільно"
  "Російська — вільно" → "Російська — вільно"
  "Польська — базовий" → "Польська — базовий"
  "Polish — A2" → "Polish — A2"
- Якщо в резюме згадана тільки англійська і немає інших мов — поверни null.
- Якщо секція Languages містить English / Англійська разом з іншими мовами, англійську перенеси тільки в english_level, а в languages залиш інші мови.

Як заповнювати work_experience_periods:

work_experience_periods:
- Витягни тільки реальні періоди роботи у компаніях, організаціях або оплачуваних проєктах.
- Не включай career break / career gap / employment gap.
- Не включай pet-проєкти, навчання, курси, самоосвіту або періоди підготовки.
- Не включай волонтерство, якщо воно не описане як професійна оплачувана робота.
- Якщо період роботи має компанію, посаду і дати — додай його в work_experience_periods.
- Якщо місяць вказаний — заповни start_month або end_month числом від 1 до 12.
- Якщо місяць не вказаний — залиш відповідне поле month = null.
- Якщо рік вказаний — заповни start_year або end_year.
- Якщо рік не вказаний — залиш відповідне поле year = null.
- Якщо робота триває зараз — is_current=true, end_month=null, end_year=null.
- Якщо робота завершена — is_current=false і заповни end_month/end_year, якщо вони вказані.
- is_commercial=true для роботи в компаніях, організаціях або оплачуваних проєктах.
- Не вигадуй дати, місяці, компанії або посади.

Приклад:
Якщо резюме містить:

Work Experience

TechNova Solutions
Period: 03.2020 - 08.2022
Position: Backend Developer

Bright Apps
Period: 06.2018 - 01.2020
Position: Junior Python Developer

Career Break
Period: 09.2022 - 12.2023
Relocation and family reasons. Completed several online courses and personal projects.

Pet Project
Task Manager API
Built a FastAPI project with PostgreSQL and Docker.

то work_experience_periods має містити тільки TechNova Solutions і Bright Apps.

Career Break не додавай у work_experience_periods.
Pet Project не додавай у work_experience_periods.

Як заповнювати sections:

Створи логічні секції резюме на основі raw text.

Для section_type використовуй короткі технічні значення англійською:
- "summary" — короткий профіль / про себе
- "skills" — навички
- "experience" — досвід роботи
- "projects" — проєкти
- "career_break" — перерва в карʼєрі, career gap, employment gap або пояснення періоду без роботи: догляд за родичем, декрет, хвороба, релокація, війна, адаптація, відновлення, навчання чи повернення до професійного розвитку після паузи
- "education" — освіта
- "languages" — мови
- "certificates" — сертифікати / курси
- "soft_skills" — особисті, комунікаційні та організаційні навички кандидата
- "other" — інша релевантна інформація
- "raw_resume" — якщо текст неможливо нормально розділити на секції

Семантична класифікація sections:
- Визначай section_type за змістом блоку, а не лише за фізичним заголовком, під яким він знаходиться в резюме.
- Якщо блок за змістом описує перерву в карʼєрі, повернення до роботи, career gap або пояснення відсутності професійного досвіду за певний період — створи окрему секцію з section_type="career_break".
- Це правило застосовується незалежно від того, де цей блок розташований у raw text: у "Досвід роботи", "Experience", "Other", наприкінці резюме або між іншими секціями.
- Не включай career_break у section_type="experience", якщо його можна відокремити як самостійний логічний блок.
- У section_type="experience" залишай тільки фактичний робочий досвід у компаніях, організаціях або оплачуваних проєктах.

career_break:
- Якщо в резюме є блок Career Break / Career gap / Employment gap / Перерва в карʼєрі / Карʼєрна пауза / Пауза в роботі — обовʼязково створи окрему секцію з section_type="career_break".
- Це правило працює незалежно від того, де блок розташований у raw text: у "Досвід роботи", "Experience", "Other", наприкінці резюме або між іншими секціями.
- У section_type="career_break" включай тільки опис перерви: період, причину паузи, релокацію, догляд, хворобу, декрет, війну, адаптацію, відновлення або повернення до професійного розвитку.
- Не включай career_break у section_type="experience".
- У section_type="experience" залишай тільки фактичний робочий досвід у компаніях, організаціях або оплачуваних проєктах.

Додаткові правила для sections:
- Якщо в резюме є блок Pet Projects / Projects / Проєкти — обовʼязково створи окрему секцію з section_type="projects".
- Не ховай pet-проєкти всередині experience, якщо в резюме вони подані окремим блоком.
- Якщо в секції projects є GitHub / demo / URL проєкту, збережи цей link у content.
- Pet-проєкти не рахуються в years_of_experience, але мають бути збережені в sections як "projects".
- Якщо в резюме є Career Break / Career gap / Employment gap / Перерва в карʼєрі / Карʼєрна пауза / Пауза в роботі — створи окрему секцію з section_type="career_break".
- Якщо опис career break знаходиться всередині блоку "Досвід роботи" / "Experience", все одно винеси його в окрему секцію "career_break".
- Не включай career break у секцію "experience", якщо його можна відокремити від реального робочого досвіду.
- У секції "experience" залишай тільки робочий досвід у компаніях, організаціях або оплачуваних проєктах.
- У секції "career_break" збережи період, причину паузи і що кандидат робив для повернення до професійного розвитку, якщо це вказано.
- Використовуй "raw_resume" тільки якщо резюме неможливо нормально розділити на логічні секції
- Якщо ти вже створив summary / skills / experience / education / languages, не додавай окрему секцію raw_resume
- Не обʼєднуй увесь текст резюме в одну секцію, якщо його можна логічно розділити
- Контактні дані, email, phone, GitHub, LinkedIn або інші URL не додавай у resume_analysis, якщо для них немає окремого поля у схемі
- Такі дані можна залишити у відповідній секції content або в секції "other"
- URL, email і phone numbers не додавай у skills

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

        print_openai_usage(
            model=settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    return parsed_resume