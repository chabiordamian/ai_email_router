from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ollama import AsyncClient

from app.health import readiness_checks
from app.routing_config import load_routing_config
from app.settings import Settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_environment()
    routing_config = load_routing_config(settings.departments_config_path)
    ollama_client = AsyncClient(
        host=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    )
    application.state.settings = settings
    application.state.routing_config = routing_config
    application.state.ollama_client = ollama_client
    try:
        yield
    finally:
        await ollama_client.close()


app = FastAPI(
    title="AI Email Router",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/health", tags=["Operations"])
async def health(request: Request) -> JSONResponse:
    checks = await readiness_checks(
        request.app.state.settings,
        request.app.state.ollama_client,
    )
    is_ready = all(status == "ok" for status in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ok" if is_ready else "unavailable",
            "checks": checks,
        },
    )
