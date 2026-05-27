from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.recordings import router as recordings_router
from app.schemas.common import ErrorResponse


def _status_to_error_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
    }
    return mapping.get(status_code, "UNEXPECTED_ERROR")


def create_app() -> FastAPI:
    app = FastAPI(title="claude-md-recording-feedback-api")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(recordings_router)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", _status_to_error_code(exc.status_code))
            message = detail.get("message", "Request failed")
            details = detail.get("details", {})
        else:
            code = _status_to_error_code(exc.status_code)
            message = str(detail) if detail else "Request failed"
            details = {}

        payload = ErrorResponse(
            code=code,
            message=message,
            details=details,
            request_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception):
        payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="解析処理に失敗しました。時間をおいて再試行してください。",
            details={},
            request_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

