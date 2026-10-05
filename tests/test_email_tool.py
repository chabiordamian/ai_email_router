import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.email_tool import EmailTool
from app.routing_config import load_routing_config
from app.settings import Settings

PROJECT_ROOT = Path(__file__).parents[1]


def make_settings() -> Settings:
    return Settings(
        departments_config_path=PROJECT_ROOT / "config" / "departments.yaml",
        ollama_base_url="http://ollama:11434",
        ollama_model="qwen3:1.7b",
        ollama_timeout_seconds=120,
        smtp_host="mailpit",
        smtp_port=1025,
        smtp_timeout_seconds=10,
        email_from="ai-router@example.com",
    )


def make_tool() -> EmailTool:
    return EmailTool(
        sender_email="jan.nowak@example.com",
        message="Nie działa firmowa sieć.",
        routing_config=load_routing_config(
            PROJECT_ROOT / "config" / "departments.yaml"
        ),
        settings=make_settings(),
    )


def test_sends_message_to_configured_department() -> None:
    with patch("app.email_tool.aiosmtplib.send", new_callable=AsyncMock) as send:
        result = asyncio.run(make_tool().send_email("it"))

    sent_message = send.await_args.args[0]
    assert sent_message["From"] == "ai-router@example.com"
    assert sent_message["To"] == "it@example.com"
    assert sent_message["Reply-To"] == "jan.nowak@example.com"
    assert sent_message["Subject"] == "New request for it"
    assert sent_message.get_content().strip() == "Nie działa firmowa sieć."
    send.assert_awaited_once_with(
        sent_message,
        hostname="mailpit",
        port=1025,
        timeout=10,
    )
    assert result == "Message sent to it"


def test_rejects_unknown_department_without_sending() -> None:
    with (
        patch("app.email_tool.aiosmtplib.send", new_callable=AsyncMock) as send,
        pytest.raises(ValueError, match="Unknown department: finance"),
    ):
        asyncio.run(make_tool().send_email("finance"))

    send.assert_not_awaited()
