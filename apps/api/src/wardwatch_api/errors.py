"""Golden error shape. Copy this for every later endpoint.

{
  "error": {
    "code": "NOT_READY",
    "message": "City config missing",
    "request_id": "..."
  }
}
"""

from __future__ import annotations

from fastapi.responses import JSONResponse


def error_body(code: str, message: str, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


def error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_body(code, message, request_id),
        headers={"X-Request-Id": request_id},
    )
