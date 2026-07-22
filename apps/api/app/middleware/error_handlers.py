"""
Global exception handlers for the FastAPI application.
Converts unhandled exceptions into consistent JSON error responses.
"""

import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware.logging import get_logger

logger = get_logger("error_handler")


def register_error_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(
            "http_error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error.get("loc", []))

            errors.append({
                "field": field,
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "value_error"),
            })

        logger.warning(
            "validation_error",
            path=str(request.url),
            error_count=len(errors),
            details=errors,
        )

        # Include specific fields in the error message for easier debugging
        err_details_str = "; ".join(f"'{err['field']}': {err['message']}" for err in errors)
        message = f"Request validation failed: {err_details_str}" if errors else "Request validation failed"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": 422,
                    "message": message,
                    "details": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        tb_str = traceback.format_exc()
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            exception_type=type(exc).__name__,
            traceback=tb_str,
        )

        from app.config import get_settings
        settings = get_settings()
        is_dev = settings.environment.lower() in ("development", "dev") or settings.debug

        if is_dev:
            # Output full exception and traceback to make local debugging much easier
            message = f"Unhandled Exception: {type(exc).__name__}: {str(exc)}\n\nTraceback:\n{tb_str}"
        else:
            message = "An unexpected error occurred. Please try again later."

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": message,
                }
            },
        )
