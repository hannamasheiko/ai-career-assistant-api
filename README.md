# AI Career Assistant API

AI Career Assistant API is a backend application for organizing and improving the job search process with artificial intelligence.

The service lets you create a candidate profile, upload and structure resumes and vacancies, assess how well a candidate fits a specific position, track applications, store the history of interactions with employers, and generate personalized content for applying to a vacancy.

The project is implemented as a REST API on FastAPI and uses OpenAI models through LangChain for structured parsing, normalization, data analysis, and content generation.

## Project Goal

The main goal of the project is to combine the key stages of the job search in one backend system:

- storing a candidate's professional data and preferences;
- turning unstructured resume and vacancy text into structured data;
- analyzing vacancy requirements;
- comparing a candidate with a chosen vacancy;
- tracking applications and communication with employers;
- generating personalized content for applying to vacancies — currently cover letters.

## Implemented in the Project

The current version implements:

- user registration and authentication;
- JWT-based access control;
- secure password hashing with bcrypt;
- candidate profile management;
- resume upload as plain text;
- AI parsing and structuring of resumes;
- commercial experience calculation at the backend level;
- vacancy upload as plain text;
- AI parsing and a separate AI analysis of vacancies;
- tracking vacancies for a specific resume;
- AI analysis of candidate-to-vacancy fit;
- AI-generated match score and recommendation based on defined criteria;
- generation of personalized cover letters;
- storage of the history of generated content variants;
- manual editing of generated content;
- tracking of interactions with employers;
- asynchronous PostgreSQL integration;
- database migrations via Alembic;
- OpenAPI documentation via Swagger UI and ReDoc;
- health-check endpoints for the application and the database;
- search for similar past applications via pgvector for the content generation context;
- management of the tracked vacancy status: automatic transitions on events, manual discarding and closing, returning to work;
- automated tests and CI.

## Technologies

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic v2
- Pydantic Settings

### Database

- PostgreSQL
- pgvector
- SQLAlchemy 2.0
- Async SQLAlchemy
- asyncpg
- Alembic

### Testing and CI

- pytest, pytest-cov
- GitHub Actions — running tests on every push

### Authentication and Security

- JWT
- OAuth2 Password Flow
- python-jose
- Passlib
- bcrypt

### AI Integration

- OpenAI API via `langchain-openai` — using OpenAI models to process resumes, vacancies, match analysis, and content generation;
- OpenAI embeddings (`text-embedding-3-small`) — vacancy embeddings for searching similar past applications;
- LangChain — building prompt templates and AI chains;
- LCEL — creating `prompt → model → structured output` pipelines;
- Pydantic structured outputs — getting typed and validated responses from the LLM;
- Prompt-based extraction and normalization — extracting and normalizing data from resumes and vacancies;
- Prompt-based analysis — analysis of vacancies and of candidate-to-vacancy fit;
- Prompt-based content generation — generation of cover letters.

## Architecture

The application is built with a modular, multi-layered architecture:

```text
Client
  ↓
FastAPI routers
  ↓
Service layer
  ├── AI chains and context builders
  │     ↓
  │   OpenAI models
  │
  └── SQLAlchemy ORM
        ↓
      PostgreSQL
```

### Main Layers

```text
app/
├── ai/
│   ├── chains/              # OpenAI and LangChain chains
│   └── context_builders/    # Preparation of structured context for AI analysis
├── api/                     # FastAPI routers and HTTP endpoints
├── core/                    # Configuration and security utilities
├── db/                      # Async database engine and session management
├── models/                  # SQLAlchemy ORM models
├── schemas/                 # Pydantic request, response, and AI-output schemas
├── services/                # Business logic and database operations
│   └── interaction_rules.py # Rules for TrackedVacancy status transitions, defined as tables
├── dependencies.py          # Shared FastAPI dependencies
└── main.py                  # Application entry point

alembic/
└── versions/                # Database migration history
```

The API layer handles HTTP requests, authentication, validation, and HTTP errors. The service layer contains business logic and database operations. AI chains are responsible for structured parsing, analysis, and text generation. Pydantic schemas are used to validate API request and response data, and to define the structured outputs that language models must return.


### Main Entities

- **User** — the user account and authentication data.
- **CandidateProfile** — the candidate's main contact and professional data, as well as preferences for roles, locations, work formats, employment types, salary, and relocation.
- **ResumeDocument** — the original resume text and document metadata.
- **ResumeAnalysis** — normalized general information about the candidate, extracted from the resume.
- **ResumeSection** — structured resume sections: work experience, projects, education, skills, career breaks, and so on.
- **Vacancy** — a global entity of the shared vacancy catalog. It does not belong to a specific user and deliberately has no `user_id`. Authenticated users can use catalog vacancies in their own job search workflow.
- **VacancyAnalysis** — AI analysis of a vacancy's requirements, responsibilities, seniority, risks, and positive signals.
- **VacancyEmbedding** — a vector representation of a vacancy for searching similar applications.
- **TrackedVacancy** — a user's personal link to a vacancy through a specific resume. This entity defines ownership and stores private state: status, priority, decision, notes, and the history of interactions.
- **MatchAnalysis** — AI assessment of how well the candidate fits the vacancy.
- **GeneratedContent** — generated and manually edited content for an application.
- **Interaction** — communication or other activity related to an application for a vacancy.

## Main Functionality

### Authentication

The authentication module supports:

- registration of a new user;
- checking the uniqueness of username and email;
- password hashing via bcrypt;
- login via OAuth2 Password Flow;
- generation of a JWT access token;
- retrieval of the currently authenticated user;
- protection of private endpoints via Bearer authentication.

Main endpoints:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Candidate Profile

An authenticated user can create and edit their own candidate profile.

The profile stores:

- desired roles;
- desired locations;
- desired work formats;
- desired employment types;
- minimum expected salary and currency;
- readiness to relocate;
- other job search settings.

Main endpoints:

```text
POST  /profile
GET   /profile/me
PATCH /profile/me
```

### Resume Processing

A resume can be submitted as plain text. The AI chain extracts structured data about the candidate and splits the document into logical sections.

The main resume processing flow:

1. receiving the original resume text;
2. extracting normalized information about the candidate;
3. identifying resume sections;
4. extracting periods of commercial work;
5. calculating the total years of commercial experience in backend code;
6. saving the original and structured data in PostgreSQL.

The language model does not calculate total experience and does not determine the candidate's seniority. These tasks are deliberately separated from the data extraction stage.

Main endpoint:

```text
POST /resumes/from-text
```

The request body must contain plain text with the `text/plain` content type.

Additional endpoints:

```text
GET   /resumes
GET   /resumes/{resume_document_id}
PATCH /resumes/{resume_document_id}
```

### Vacancy Processing

A vacancy can be submitted as plain text, copied from a job board or another source.

The vacancy parser extracts and normalizes:

- company name;
- position title;
- source and source URL;
- location;
- work format;
- employment type;
- salary range and currency;
- cleaned vacancy text.

Main endpoint:

```text
POST /vacancies/from-text
```

An embedding of the vacancy is created immediately on creation.

The optional query parameter `analyze=true` creates the vacancy and immediately starts its AI analysis. If the analysis fails, the vacancy is still returned with `analysis: null`; the analysis can be retried via `POST /vacancies/{vacancy_id}/analysis`.

### Vacancy Ownership Model

`Vacancy` is a global entity of the shared catalog, not a private resource of a user. Therefore it has no `user_id`, and access to a vacancy is not filtered by user.

Personalization and access control start at the `TrackedVacancy` level. A user can view and modify only those tracked vacancies that are linked to their own resume document.

### Vacancy Analysis

Vacancy analysis is separated from vacancy parsing and can be run independently.

The AI analysis determines:

- the expected experience level;
- the required English level;
- required skills;
- optional skills;
- main responsibilities;
- red flags;
- green flags;
- a summary of the vacancy;
- an overall recommendation about the vacancy.

Main endpoints:

```text
POST /vacancies/{vacancy_id}/analysis
GET  /vacancies/{vacancy_id}/analysis
```

### Tracked Vacancies

A vacancy can be linked to a specific resume and added to the application tracking process.

TrackedVacancy stores:

- the current `status`;
- `priority` and `decision`;
- `notes`;
- `applied_at` — the date the resume was sent;
- `closed_at` — the date work on the vacancy was completed;
- `next_action_at` — a reminder.

The same vacancy cannot be linked again to the same resume.

Main endpoints:

```text
POST  /tracked-vacancies
GET   /tracked-vacancies
GET   /tracked-vacancies/{tracked_vacancy_id}
PATCH /tracked-vacancies/{tracked_vacancy_id}
POST  /tracked-vacancies/{tracked_vacancy_id}/reopen
```

### Statuses of TrackedVacancy

The status moves mainly through events (interactions): an incoming message from a recruiter, an interview, a test task, an offer, or a rejection. Manually, a vacancy can only be discarded (`discarded`) or closed (`closed`), and returned to work through the `reopen` endpoint. After a reopen, the status is recalculated from the history of interactions.

Full description of transitions, restrictions, and date rules: [docs/tracked-vacancy-status-flow.md](docs/tracked-vacancy-status-flow.md).

### Candidate-to-Vacancy Match Analysis

The match analysis module compares the candidate with a chosen vacancy, using:

- the CandidateProfile settings;
- the normalized ResumeAnalysis;
- detailed ResumeSections;
- the original resume text;
- normalized Vacancy data;
- VacancyAnalysis;
- the cleaned vacancy text.

The analysis is performed from the combined perspective of an IT recruiter and a technical hiring manager.

The result contains:

- a match score from 0 to 100;
- a recommendation category;
- strong matches;
- partial matches;
- missing skills;
- risk points;
- a reasoning summary.

The prompt defines the following rules for matching the match score to the recommendation:

```text
85–100  strong_match
70–84   good_match
55–69   partial_match
40–54   weak_match
0–39    not_recommended
```

Each TrackedVacancy stores only one current MatchAnalysis. A repeated run updates the existing result.

Main endpoints:

```text
POST /tracked-vacancies/{tracked_vacancy_id}/match-analysis
GET  /tracked-vacancies/{tracked_vacancy_id}/match-analysis
```

### Generated Content

The application can generate personalized content for applying to a vacancy, based on the resume, the vacancy, and the available MatchAnalysis.

The only content type implemented so far is:

- cover letter.

Generation supports:

- language selection;
- tone selection;
- additional user instructions;
- storing a separate record for each new generation;
- manual editing of the saved content.

The resume remains the main source of facts about the candidate. The AI must not invent commercial experience, skills, achievements, motivation, or company information.

Main endpoints:

```text
POST  /tracked-vacancies/{tracked_vacancy_id}/generated-content/generate
GET   /tracked-vacancies/{tracked_vacancy_id}/generated-content
GET   /tracked-vacancies/generated-content/{generated_content_id}
PATCH /tracked-vacancies/generated-content/{generated_content_id}
```

For the generation context, the application searches for similar past applications via pgvector: vacancies with a close embedding and their outcomes (status and dates) are passed to the model as historical context.

### Interaction Tracking

The application stores activities and communication related to a TrackedVacancy. Interaction types:

- `resume_sent` — sending a resume;
- `message`, `call` — a message or a phone call;
- `screening_questions` — screening questions;
- `interview_invitation` — an invitation to an interview;
- `hr_interview`, `technical_interview`, `final_interview` — interviews;
- `test_task` — a test task;
- `feedback` — feedback;
- `offer_discussion`, `offer` — offer discussion and an offer;
- `rejection` — a rejection.

The direction (`incoming` / `outgoing`) is set for each type separately: `resume_sent` is only `outgoing`, `offer` is only `incoming`, and `rejection` requires a direction.

Main endpoints:

```text
POST   /tracked-vacancies/{tracked_vacancy_id}/interactions
GET    /tracked-vacancies/{tracked_vacancy_id}/interactions
GET    /tracked-vacancies/interactions/{interaction_id}
PATCH  /tracked-vacancies/interactions/{interaction_id}
DELETE /tracked-vacancies/interactions/{interaction_id}
```

The type and direction of an interaction cannot be edited after creation: a mistake is fixed by deleting the interaction and entering it again.

## Main Application Flow

```text
1. User registration
   ↓
2. Login and receiving a JWT access token
   ↓
3. Creating a CandidateProfile
   ↓
4. Submitting the resume text
   ↓
5. Parsing and saving the resume
   ↓
6. Submitting the vacancy text
   ↓
7. Parsing and analyzing the vacancy
   ↓
8. Linking the vacancy to the chosen resume
   ↓
9. Generating the Candidate-to-Vacancy MatchAnalysis
   ↓
10. Generating a personalized cover letter
   ↓
11. Tracking the application status and interactions with the employer
```

## Running the Application

### Prerequisites

Before running the application, install:

- Python 3.11 or newer
- PostgreSQL;
- Git.

Resume parsing, vacancy parsing, vacancy analysis, match analysis, and content generation require an OpenAI API key.

### 1. Cloning the Repository

```bash
git clone https://github.com/hannamasheiko/ai-career-assistant-api.git
cd ai-career-assistant-api
```

### 2. Creating a Virtual Environment

```bash
python -m venv .venv
```

Activation on macOS or Linux:

```bash
source .venv/bin/activate
```

Activation on Windows:

```bash
.venv\Scripts\activate
```

### 3. Installing Dependencies

```bash
pip install -r requirements.txt
```

### 4. Creating the PostgreSQL Database

Create a local PostgreSQL database and user. The values used in the example configuration:

```text
Database: ai_career_assistant_db
User:     ai_career_user
Password: ai_career_password
Port:     5435
```

A separate `ai_career_test_db` database is needed for the tests (`TEST_DATABASE_URL`). Create it with the same user and port.

The port and credentials can be changed via environment variables.

### 5. Configuring Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Configure `.env`:

```env
PROJECT_NAME=AI Career Assistant API
API_VERSION=0.1.0
ENVIRONMENT=development

DATABASE_URL=postgresql+asyncpg://ai_career_user:ai_career_password@localhost:5435/ai_career_assistant_db

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT=90
OPENAI_MAX_RETRIES=2

OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

SECRET_KEY=replace_with_a_long_random_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

The full list of variables with comments is in `.env.example`. The access token lives 8 hours by default.

Do not add `.env` or real secrets to version control.

A safe development secret can be generated with the command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 6. Applying Database Migrations

```bash
alembic upgrade head
```

Creating a new migration after changing the SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe migration"
```

Rolling back the last migration:

```bash
alembic downgrade -1
```

### 7. Running the Application

#### With Docker

To run the AI Career Assistant API and PostgreSQL, execute:

```bash
docker compose up --build
```

After startup, the API is available at:

```text
http://localhost:8004
```

#### Locally

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## API Documentation

FastAPI automatically generates interactive OpenAPI documentation.

When running via Docker Compose:

```text
Swagger UI:    http://localhost:8004/docs
ReDoc:         http://localhost:8004/redoc
OpenAPI schema: http://localhost:8004/openapi.json
```

When running locally:

```text
Swagger UI:    http://127.0.0.1:8000/docs
ReDoc:         http://127.0.0.1:8000/redoc
OpenAPI schema: http://127.0.0.1:8000/openapi.json
```

Protected endpoints can be tested in Swagger UI: log in, copy the received access token, and use the **Authorize** button.

The full list of response codes is in Swagger. The most important ones for tracking vacancies:

- `400` — a rule about the interaction direction was violated;
- `409` — the tracked vacancy status does not allow the action;
- `422` — invalid data or a forbidden field in the request;
- `503` — the AI service is not configured (for example, `OPENAI_API_KEY` is missing).

## Health Checks

Checking the application status:

```text
GET /health
```

Checking the database connection (returns `503` if the database is unavailable):

```text
GET /db-health
```

Root endpoint:

```text
GET /
```

## Tests

Running all tests:

```bash
pytest
```

The tests use a separate database set via `TEST_DATABASE_URL` (it is in `.env.example`). The name of this database must contain the word `test` as a separate word (for example, `ai_career_test_db`), and it must differ from `DATABASE_URL`. Otherwise the tests will not run, so that the main database is not wiped. Tests that use the database create and drop tables in this database, so they do not touch the main database.

The tests do not call the real model: AI calls are replaced with mocks. The separate AI eval tests (`ai_eval`) call OpenAI, are disabled by default, and are run like this:

```bash
pytest -m ai_eval
```

GitHub Actions runs `pytest` on every push.

## Principles of the AI Layer

The AI layer follows these rules:

- structured outputs are validated through Pydantic schemas;
- extraction is separated from evaluation;
- resume parsing does not determine the candidate's seniority;
- commercial experience is separated from pet projects and career breaks;
- total commercial experience is calculated by backend code;
- vacancy parsing is separated from vacancy evaluation;
- match analysis uses structured data as its main source;
- generated content must not contain unconfirmed facts about the candidate;
- prompts contain protection against instructions embedded in resume or vacancy text;
- the model name and prompt version are stored together with AI-generated records where the models provide for it.

## Database Migrations

Alembic is used to version and update the PostgreSQL schema.

The current migration history includes:

- creation of the application's main tables;
- the users table and the link between a user and a CandidateProfile;
- unique constraints for the resume-to-vacancy link;
- a constraint allowing one current MatchAnalysis per TrackedVacancy;
- professional preference fields of the CandidateProfile;
- check constraints for the TrackedVacancy and Interaction fields;
- renaming `last_contact_at` to `closed_at`;
- a table of vacancy embeddings (`vacancy_embeddings`) and the `vector` extension for pgvector.

After receiving changes to the models or the database schema, apply the latest migrations:

```bash
alembic upgrade head
```
