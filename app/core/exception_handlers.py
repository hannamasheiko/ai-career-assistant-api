from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    AIOutputValidationError,
    AIPrerequisiteError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)


async def ai_timeout_exception_handler(
    request: Request,
    exc: AITimeoutError,
) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={
            "detail": "AI service timed out. Please try again later.",
        },
    )


async def ai_rate_limit_exception_handler(
    request: Request,
    exc: AIRateLimitError,
) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "AI service rate limit exceeded. Please try again later.",
        },
    )


async def ai_output_validation_exception_handler(
    request: Request,
    exc: AIOutputValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": "AI service returned an invalid response.",
        },
    )


async def ai_service_exception_handler(
    request: Request,
    exc: AIServiceError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "AI service is temporarily unavailable. Please try again later.",
        },
    )

async def ai_prerequisite_exception_handler(
    request: Request,
    exc: AIPrerequisiteError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
        },
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        AITimeoutError,
        ai_timeout_exception_handler,
    )
    app.add_exception_handler(
        AIRateLimitError,
        ai_rate_limit_exception_handler,
    )
    app.add_exception_handler(
        AIOutputValidationError,
        ai_output_validation_exception_handler,
    )
    app.add_exception_handler(
        AIServiceError,
        ai_service_exception_handler,
    )
    app.add_exception_handler(
        AIPrerequisiteError,
        ai_prerequisite_exception_handler,
    )

