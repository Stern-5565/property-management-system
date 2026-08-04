"""Application-defined exceptions and centralized FastAPI exception handlers.

Every error response (whether raised deliberately via AppError, a request
validation failure, an HTTP error, or an unhandled exception) is normalized
to the same shape:

    {"error": {"code": "...", "message": "...", "details": {...}}}

See documentation/project-scope.md, section 13, for the agreed error format.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Raise this for any deliberate business/validation failure in the app.

    Example: raise AppError("TENANCY_DATE_CONFLICT", "This property already
    has a tenancy covering those dates.", status_code=409)
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Each error dict's "ctx" field can hold the raw exception object
        # from a custom validator (e.g. the ValueError raised in
        # LandlordWriteBase.require_company_or_full_name) - that object
        # isn't JSON-serializable and would crash this handler. Strip it
        # out; the human-readable "msg" string is already present without
        # it. (Pydantic's own ValidationError.errors() has
        # include_context=False for this, but FastAPI's
        # RequestValidationError.errors() - a different method - doesn't
        # accept that kwarg, so we filter manually instead.)
        errors = [{key: value for key, value in error.items() if key != "ctx"} for error in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("VALIDATION_ERROR", "One or more fields failed validation.", {"errors": errors}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", str(exc.detail), {}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Full details go to the log, never to the client - an unhandled
        # exception could otherwise leak internal state (stack traces,
        # connection strings, etc) to whoever made the request.
        logger.exception("Unhandled exception while handling %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", {}),
        )
