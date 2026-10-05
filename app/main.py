from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ollama import AsyncClient
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.agent import AgentResponseError, RoutingAgent
from app.health import readiness_checks
from app.routing_config import load_routing_config
from app.settings import Settings

MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RoutingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    message: MessageText


class RoutingResponse(BaseModel):
    department: str
    response: str


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
    application.state.routing_agent = RoutingAgent(
        client=ollama_client,
        routing_config=routing_config,
        settings=settings,
    )
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


@app.post(
    "/api/v1/messages",
    response_model=RoutingResponse,
    tags=["Messages"],
)
async def route_message(
    payload: RoutingRequest,
    request: Request,
) -> RoutingResponse:
    try:
        result = await request.app.state.routing_agent.route(
            sender_email=str(payload.email),
            message=payload.message,
        )
    except AgentResponseError as error:
        raise HTTPException(
            status_code=502,
            detail="The model returned an invalid routing decision",
        ) from error

    return RoutingResponse(
        department=result.department,
        response=result.response,
    )
