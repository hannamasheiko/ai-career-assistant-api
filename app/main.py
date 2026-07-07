from fastapi import FastAPI

from app.api.db_health import router as db_health_router
from app.api.health import router as health_router
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.resumes import router as resumes_router


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
)

@app.get("/")
def root():
    return {
        "message": "AI Career Assistant API",
        "docs": "/docs",
        "health": "/health",
    }

app.include_router(health_router)
app.include_router(db_health_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(resumes_router)

