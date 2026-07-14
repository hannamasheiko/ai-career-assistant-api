# AI Career Assistant API

AI Career Assistant API — це backend-застосунок для організації та покращення процесу пошуку роботи за допомогою штучного інтелекту.

Сервіс дозволяє створювати профіль кандидата, завантажувати й структурувати резюме та вакансії, оцінювати відповідність кандидата конкретній позиції, відстежувати відгуки, зберігати історію взаємодії з роботодавцями та генерувати персоналізований контент для подання на вакансію.

Проєкт реалізований як REST API на FastAPI та використовує OpenAI API через LangChain для структурованого AI-аналізу.

## Мета проєкту

Головна мета проєкту — об’єднати основні етапи пошуку роботи в одній backend-системі:

- зберігання професійних даних і побажань кандидата;
- перетворення неструктурованого тексту резюме та вакансій у структуровані дані;
- аналіз вимог вакансії;
- порівняння кандидата з обраною вакансією;
- відстеження відгуків і комунікації з роботодавцями;
- генерація персоналізованих супровідних листів та іншого контенту для подання.

## Реалізовано в проєкті

У поточній версії реалізовано:

- реєстрацію та автентифікацію користувачів;
- контроль доступу на основі JWT;
- безпечне хешування паролів за допомогою bcrypt;
- керування профілем кандидата;
- завантаження резюме як plain text;
- AI-парсинг і структуризацію резюме;
- розрахунок комерційного досвіду на backend-рівні;
- завантаження вакансій як plain text;
- AI-парсинг та окремий AI-аналіз вакансій;
- відстеження вакансій для конкретного резюме;
- AI-аналіз відповідності кандидата вакансії;
- розрахунок match score та формування recommendation;
- генерацію персоналізованих cover letter;
- збереження історії згенерованого та відредагованого контенту;
- відстеження взаємодій із роботодавцями;
- асинхронну інтеграцію з PostgreSQL;
- міграції бази даних через Alembic;
- OpenAPI-документацію через Swagger UI та ReDoc;
- health-check endpoints для застосунку та бази даних;
- логування використаних OpenAI tokens і приблизної вартості запитів.

## Технології

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic v2
- Pydantic Settings

### Database

- PostgreSQL
- SQLAlchemy 2.0
- Async SQLAlchemy
- asyncpg
- Alembic

### Authentication and Security

- JWT
- OAuth2 Password Flow
- python-jose
- Passlib
- bcrypt

### AI Integration

- OpenAI API via `langchain-openai` — використання моделей OpenAI для обробки резюме, вакансій, match analysis і генерації контенту;
- LangChain — побудова prompt templates та AI chains;
- LCEL — створення pipeline-послідовностей `prompt → model → structured output`;
- Pydantic structured outputs — отримання типізованих і валідованих відповідей від LLM;
- Prompt-based extraction and normalization — витягування та нормалізація даних із резюме й вакансій;
- Prompt-based analysis — аналіз вакансій і відповідності кандидата;
- Prompt-based content generation — генерація супровідних листів.

## Архітектура

Застосунок побудований за модульною багатошаровою архітектурою:

```text
Client
  ↓
FastAPI routers
  ↓
Service layer
  ↓
AI chains and context builders
  ↓
SQLAlchemy models
  ↓
PostgreSQL
```

### Основні шари

```text
app/
├── ai/
│   ├── chains/              # OpenAI та LangChain chains
│   └── context_builders/    # Підготовка структурованого контексту для AI-аналізу
├── api/                     # FastAPI routers та HTTP endpoints
├── core/                    # Конфігурація і security utilities
├── db/                      # Async database engine та session management
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request, response та AI-output schemas
├── services/                # Бізнес-логіка й операції з базою даних
├── dependencies.py          # Спільні FastAPI dependencies
└── main.py                  # Точка входу застосунку

alembic/
└── versions/                # Історія міграцій бази даних
```

API layer обробляє HTTP-запити, автентифікацію, валідацію та HTTP errors. Service layer містить бізнес-логіку й операції з базою даних. AI chains відповідають за структурований парсинг, аналіз і генерацію тексту. Pydantic schemas визначають контракти між API, бізнес-логікою та відповідями language model.


### Основні сутності

- **User** — обліковий запис і дані для автентифікації.
- **CandidateProfile** — професійні побажання кандидата: бажані ролі, локації, формати роботи, типи зайнятості, очікувана зарплата та готовність до relocation.
- **ResumeDocument** — оригінальний текст резюме та метадані документа.
- **ResumeAnalysis** — нормалізована загальна інформація про кандидата, отримана з резюме.
- **ResumeSection** — структуровані секції резюме: work experience, projects, education, skills, career breaks тощо.
- **Vacancy** — нормалізовані дані вакансії та її оригінальний текст.
- **VacancyAnalysis** — AI-аналіз вимог, обов’язків, seniority, ризиків і позитивних сигналів вакансії.
- **TrackedVacancy** — вакансія, яку кандидат відстежує через конкретне резюме.
- **MatchAnalysis** — AI-оцінка відповідності кандидата вакансії.
- **GeneratedContent** — згенерований і вручну відредагований контент для подання.
- **Interaction** — комунікація або інша активність, пов’язана з відгуком на вакансію.

## Основний функціонал

### Authentication

Модуль автентифікації підтримує:

- реєстрацію нового користувача;
- перевірку унікальності username та email;
- хешування паролів через bcrypt;
- login через OAuth2 Password Flow;
- генерацію JWT access token;
- отримання поточного автентифікованого користувача;
- захист приватних endpoints через Bearer authentication.

Основні endpoints:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Candidate Profile

Автентифікований користувач може створити та редагувати власний профіль кандидата.

Профіль зберігає:

- бажані ролі;
- бажані локації;
- бажані формати роботи;
- бажані типи зайнятості;
- мінімальну очікувану зарплату та валюту;
- готовність до relocation;
- інші налаштування пошуку роботи.

Основні endpoints:

```text
POST  /profile
GET   /profile/me
PATCH /profile/me
```

### Resume Processing

Резюме можна передати у вигляді plain text. AI chain витягує структуровані дані про кандидата та розділяє документ на логічні секції.

Основний flow обробки резюме:

1. отримання оригінального тексту резюме;
2. витягування нормалізованої інформації про кандидата;
3. визначення секцій резюме;
4. витягування періодів комерційної роботи;
5. розрахунок загальної кількості років комерційного досвіду у backend-коді;
6. збереження оригінальних і структурованих даних у PostgreSQL.

Language model не розраховує загальний досвід і не визначає seniority кандидата. Ці задачі навмисно відокремлені від етапу витягування даних.

Основний endpoint:

```text
POST /resumes/from-text
```

Request body має містити plain text із `text/plain` content type.

### Vacancy Processing

Вакансію можна передати як plain text, скопійований із job board або іншого джерела.

Vacancy parser витягує та нормалізує:

- company name;
- position title;
- source та source URL;
- location;
- work format;
- employment type;
- salary range та currency;
- cleaned vacancy text.

Основний endpoint:

```text
POST /vacancies/from-text
```

Optional query parameter `analyze=true` дозволяє створити вакансію та одразу запустити її AI-аналіз.

### Vacancy Analysis

Аналіз вакансії відокремлений від її парсингу та може запускатися незалежно.

AI-аналіз визначає:

- очікуваний experience level;
- необхідний English level;
- required skills;
- optional skills;
- основні responsibilities;
- red flags;
- green flags;
- summary вакансії;
- загальну recommendation щодо вакансії.

Основний endpoint:

```text
POST /vacancies/{vacancy_id}/analysis
```

### Tracked Vacancies

Вакансію можна пов’язати з конкретним резюме та додати до процесу відстеження відгуків.

TrackedVacancy зберігає:

- поточний application status;
- priority;
- notes;
- source URL;
- application date;
- last contact date;
- next action та його due date.

Одна й та сама вакансія не може бути повторно пов’язана з тим самим резюме.

Основні endpoints:

```text
POST  /tracked-vacancies
GET   /tracked-vacancies
GET   /tracked-vacancies/{tracked_vacancy_id}
PATCH /tracked-vacancies/{tracked_vacancy_id}
```

### Candidate-to-Vacancy Match Analysis

Модуль match analysis порівнює кандидата з обраною вакансією, використовуючи:

- налаштування CandidateProfile;
- нормалізований ResumeAnalysis;
- деталізовані ResumeSection;
- оригінальний текст резюме;
- нормалізовані дані Vacancy;
- VacancyAnalysis;
- cleaned vacancy text.

Аналіз виконується з поєднаної позиції IT recruiter та technical hiring manager.

Результат містить:

- match score від 0 до 100;
- recommendation category;
- strong matches;
- partial matches;
- missing skills;
- risk points;
- reasoning summary.

Категорії recommendation:

```text
85–100  strong_match
70–84   good_match
55–69   partial_match
40–54   weak_match
0–39    not_recommended
```

Для кожної TrackedVacancy зберігається лише один актуальний MatchAnalysis. Повторний запуск оновлює наявний результат.

Основні endpoints:

```text
POST /tracked-vacancies/{tracked_vacancy_id}/match-analysis
GET  /tracked-vacancies/{tracked_vacancy_id}/match-analysis
```

### Generated Content

Застосунок може генерувати персоналізований контент для подання на вакансію на основі резюме, вакансії та доступного MatchAnalysis.

Наразі реалізований тип контенту:

- cover letter.

Генерація підтримує:

- вибір мови;
- вибір tone;
- додаткові інструкції користувача;
- історію версій;
- ручне редагування контенту.

Резюме залишається основним джерелом фактів про кандидата. AI не повинен вигадувати комерційний досвід, skills, achievements, motivation або дані про компанію.

Основні endpoints:

```text
POST  /tracked-vacancies/{tracked_vacancy_id}/generated-content/generate
GET   /tracked-vacancies/{tracked_vacancy_id}/generated-content
GET   /generated-content/{generated_content_id}
PATCH /generated-content/{generated_content_id}
```

### Interaction Tracking

Застосунок зберігає активності та комунікацію, пов’язані з TrackedVacancy, наприклад:

- подання заявки;
- повідомлення recruiter;
- відповідь роботодавця;
- телефонний дзвінок;
- interview;
- follow-up;
- інші події, пов’язані з відгуком.

Основні endpoints:

```text
POST  /tracked-vacancies/{tracked_vacancy_id}/interactions
GET   /tracked-vacancies/{tracked_vacancy_id}/interactions
GET   /tracked-vacancies/interactions/{interaction_id}
PATCH /tracked-vacancies/interactions/{interaction_id}
```

## Основний flow застосунку

```text
1. Реєстрація користувача
   ↓
2. Login та отримання JWT access token
   ↓
3. Створення CandidateProfile
   ↓
4. Передавання тексту резюме
   ↓
5. Парсинг і збереження резюме
   ↓
6. Передавання тексту вакансії
   ↓
7. Парсинг та аналіз вакансії
   ↓
8. Прив’язка вакансії до обраного резюме
   ↓
9. Генерація Candidate-to-Vacancy MatchAnalysis
   ↓
10. Генерація персоналізованого cover letter
   ↓
11. Відстеження application status і взаємодій із роботодавцем
```

## Локальний запуск

### Передумови

Перед запуском застосунку необхідно встановити:

- Python 3.11 або новіший;
- PostgreSQL;
- Git.

Для resume parsing, vacancy parsing, vacancy analysis, match analysis і content generation потрібен OpenAI API key.

### 1. Клонування репозиторію

```bash
git clone https://github.com/hannamasheiko/ai-career-assistant-api.git
cd ai-career-assistant-api
```

### 2. Створення virtual environment

```bash
python -m venv .venv
```

Активація на macOS або Linux:

```bash
source .venv/bin/activate
```

Активація на Windows:

```bash
.venv\Scripts\activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Створення PostgreSQL database

Створіть локальну PostgreSQL database та користувача. Значення, які використовуються в прикладі конфігурації:

```text
Database: ai_career_assistant_db
User:     ai_career_user
Password: ai_career_password
Port:     5435
```

Port та credentials можна змінити через environment variables.

### 5. Налаштування environment variables

Скопіюйте приклад environment file:

```bash
cp .env.example .env
```

Налаштуйте `.env`:

```env
PROJECT_NAME=AI Career Assistant API
API_VERSION=0.1.0
ENVIRONMENT=development

DATABASE_URL=postgresql+asyncpg://ai_career_user:ai_career_password@localhost:5435/ai_career_assistant_db

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini

SECRET_KEY=replace_with_a_long_random_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Не додавайте `.env` або реальні secrets до version control.

Безпечний development secret можна згенерувати командою:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 6. Застосування database migrations

```bash
alembic upgrade head
```

Створення нової migration після зміни SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe migration"
```

Відкат останньої migration:

```bash
alembic downgrade -1
```

### 7. Запуск застосунку

```bash
uvicorn app.main:app --reload
```

API буде доступний за адресою:

```text
http://127.0.0.1:8000
```

## API-документація

FastAPI автоматично генерує інтерактивну OpenAPI-документацію.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

Protected endpoints можна тестувати у Swagger UI: виконайте login, скопіюйте отриманий access token і скористайтеся кнопкою **Authorize**.

## Health Checks

Перевірка стану застосунку:

```text
GET /health
```

Перевірка підключення до бази даних:

```text
GET /db-health
```

Root endpoint:

```text
GET /
```

## Принципи роботи AI-шару

AI layer дотримується таких правил:

- structured outputs проходять валідацію через Pydantic schemas;
- extraction відокремлений від evaluation;
- resume parsing не визначає seniority кандидата;
- commercial experience відокремлюється від pet projects і career breaks;
- загальний commercial experience розраховується backend-кодом;
- vacancy parsing відокремлений від vacancy evaluation;
- match analysis використовує structured data як основне джерело;
- generated content не повинен містити непідтверджені факти про кандидата;
- prompts містять захист від інструкцій, вбудованих у текст резюме або вакансії;
- model name і prompt version зберігаються разом з AI-generated records там, де це передбачено моделями.

## Міграції бази даних

Alembic використовується для версіонування й оновлення PostgreSQL schema.

Поточна історія migrations включає:

- створення основних таблиць застосунку;
- таблиці та зв’язки для authentication;
- unique constraints для зв’язку resume-to-vacancy;
- обмеження одного актуального MatchAnalysis для кожної TrackedVacancy;
- поля професійних побажань CandidateProfile.

Після отримання змін у models або database schema застосуйте останні migrations:

```bash
alembic upgrade head
```