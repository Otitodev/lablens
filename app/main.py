from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import router
from app.config import get_settings
from app.errors import AppError
from app.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LabLens MCP",
    version="1.0.0",
    description="Medical laboratory intelligence MCP server.",
)
app.include_router(router)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "; ".join(error["msg"] for error in exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": message,
            }
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "LabLens MCP",
        "status": "running",
    }
