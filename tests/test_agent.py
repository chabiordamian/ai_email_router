import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from ollama import AsyncClient, ChatResponse, Message

from app.agent import AgentResponseError, RoutingAgent
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


def make_agent(client: AsyncClient) -> RoutingAgent:
    return RoutingAgent(
        client=client,
        routing_config=load_routing_config(
            PROJECT_ROOT / "config" / "departments.yaml"
        ),
        settings=make_settings(),
    )


def tool_call(department: str) -> Message.ToolCall:
    return Message.ToolCall(
        function=Message.ToolCall.Function(
            name="send_email",
            arguments={"department": department},
        )
    )


def test_routes_message_by_calling_email_tool() -> None:
    client = AsyncMock(spec=AsyncClient)
    client.chat.return_value = ChatResponse(
        message=Message(role="assistant", tool_calls=[tool_call("it")])
    )

    with patch("app.agent.EmailTool.send_email", new_callable=AsyncMock) as send_email:
        send_email.return_value = "Message sent to it"
        result = asyncio.run(
            make_agent(client).route(
                sender_email="jan.nowak@example.com",
                message="Nie działa firmowa sieć.",
            )
        )

    send_email.assert_awaited_once_with("it")
    assert result.department == "it"
    assert result.response == "Message sent to it"

    client.chat.assert_awaited_once()
    decision_call = client.chat.await_args
    tool_schema = decision_call.kwargs["tools"][0]
    assert tool_schema["function"]["parameters"]["properties"]["department"][
        "enum"
    ] == ["human-resources", "help-desk", "it", "kadry", "other"]
    assert decision_call.kwargs["think"] is False
    assert decision_call.kwargs["options"] == {"temperature": 0}


@pytest.mark.parametrize("calls", [None, [], [tool_call("it"), tool_call("other")]])
def test_rejects_missing_or_multiple_tool_calls(
    calls: list[Message.ToolCall] | None,
) -> None:
    client = AsyncMock(spec=AsyncClient)
    client.chat.return_value = ChatResponse(
        message=Message(role="assistant", tool_calls=calls)
    )

    with (
        patch("app.agent.EmailTool.send_email", new_callable=AsyncMock) as send_email,
        pytest.raises(AgentResponseError),
    ):
        asyncio.run(
            make_agent(client).route(
                sender_email="jan.nowak@example.com",
                message="Test message",
            )
        )

    send_email.assert_not_awaited()


def test_rejects_unknown_department_without_sending() -> None:
    client = AsyncMock(spec=AsyncClient)
    client.chat.return_value = ChatResponse(
        message=Message(role="assistant", tool_calls=[tool_call("finance")])
    )

    with (
        patch("app.agent.EmailTool.send_email", new_callable=AsyncMock) as send_email,
        pytest.raises(AgentResponseError, match="unknown department: finance"),
    ):
        asyncio.run(
            make_agent(client).route(
                sender_email="jan.nowak@example.com",
                message="Test message",
            )
        )

    send_email.assert_not_awaited()


def test_rejects_additional_tool_arguments_without_sending() -> None:
    client = AsyncMock(spec=AsyncClient)
    call = tool_call("kadry")
    call.function.arguments["message"] = "Test message"
    client.chat.return_value = ChatResponse(
        message=Message(role="assistant", tool_calls=[call])
    )

    with (
        patch("app.agent.EmailTool.send_email", new_callable=AsyncMock) as send_email,
        pytest.raises(AgentResponseError, match="exactly one department argument"),
    ):
        asyncio.run(
            make_agent(client).route(
                sender_email="jan.nowak@example.com",
                message="Test message",
            )
        )

    send_email.assert_not_awaited()
