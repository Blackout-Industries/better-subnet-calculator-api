from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.status_code = status_code

    def to_envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "field": self.field,
            }
        }


async def api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, APIError)
    return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())


async def validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = first.get("loc", ())
        # Drop the leading "body" segment so the field path matches the request shape.
        field_parts = [str(p) for p in loc if p != "body"]
        field = ".".join(field_parts) if field_parts else None
        message = str(first.get("msg", "validation error"))
        err_type = str(first.get("type", "validation_error"))
        code = "INVALID_INPUT" if err_type != "value_error" else "INVALID_VALUE"
    else:
        field = None
        message = "validation error"
        code = "INVALID_INPUT"

    body = {
        "error": {
            "code": code,
            "message": message,
            "field": field,
        }
    }
    return JSONResponse(status_code=422, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
