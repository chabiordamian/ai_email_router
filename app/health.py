import asyncio
import logging

from aiosmtplib import SMTP
from ollama import AsyncClient

from app.settings import Settings

logger = logging.getLogger(__name__)


async def _check_ollama(client: AsyncClient, model: str) -> str:
    try:
        await client.show(model)
    except Exception as error:
        logger.warning("Ollama readiness check failed: %s", type(error).__name__)
        return "unavailable"
    return "ok"


async def _check_smtp(settings: Settings) -> str:
    client = SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    )
    try:
        await client.connect()
        await client.quit()
    except Exception as error:
        logger.warning("SMTP readiness check failed: %s", type(error).__name__)
        return "unavailable"
    finally:
        client.close()
    return "ok"


async def readiness_checks(
    settings: Settings, ollama_client: AsyncClient
) -> dict[str, str]:
    ollama_status, smtp_status = await asyncio.gather(
        _check_ollama(ollama_client, settings.ollama_model),
        _check_smtp(settings),
    )
    return {"ollama": ollama_status, "smtp": smtp_status}
