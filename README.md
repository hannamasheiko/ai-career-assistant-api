# AI Career Assistant API

AI Career Assistant API is a FastAPI backend project for analyzing how well a candidate's resume matches job vacancies.

The MVP flow:

```text
Resume text → Resume parsing → Vacancy text → Vacancy parsing → Match analysis 
```

## Tech stack

Поточний:

- Python
- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- PostgreSQL
- Docker Compose
- SQLAlchemy
- Async SQLAlchemy
- asyncpg

Запланований:

- Alembic
- LangChain
- OpenAI API
- LCEL chains
- Pydantic structured AI outputs
- RAG
- vector store
- background jobs
- agent with tools