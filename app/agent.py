from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ollama import AsyncClient, Message

from app.email_tool import EmailTool
from app.routing_config import RoutingConfig
from app.settings import Settings

TOOL_NAME = "send_email"


class AgentResponseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentResult:
    department: str
    response: str


class RoutingAgent:
    def __init__(
        self,
        *,
        client: AsyncClient,
        routing_config: RoutingConfig,
        settings: Settings,
    ) -> None:
        self._client = client
        self._routing_config = routing_config
        self._settings = settings

    async def route(self, *, sender_email: str, message: str) -> AgentResult:
        email_tool = EmailTool(
            sender_email=sender_email,
            message=message,
            routing_config=self._routing_config,
            settings=self._settings,
        )
        messages = [
            Message(role="system", content=self._system_prompt()),
            Message(role="user", content=message),
        ]

        decision = await self._client.chat(
            model=self._settings.ollama_model,
            messages=messages,
            tools=[self._tool_schema()],
            think=False,
        )
        tool_call = self._single_tool_call(decision.message.tool_calls)
        department = self._department_argument(tool_call.function.arguments)
        tool_result = await email_tool.send_email(department)

        messages.extend(
            [
                decision.message,
                Message(
                    role="tool",
                    tool_name=TOOL_NAME,
                    content=tool_result,
                ),
            ]
        )
        completion = await self._client.chat(
            model=self._settings.ollama_model,
            messages=messages,
            think=False,
        )
        response = (completion.message.content or "").strip()
        if not response:
            raise AgentResponseError("Model returned an empty final response")

        return AgentResult(department=department, response=response)

    def _system_prompt(self) -> str:
        department_lines = []
        for department in self._routing_config.departments:
            examples = "; ".join(department.examples)
            department_lines.append(
                f"- {department.id}: {department.description} Examples: {examples}"
            )

        departments = "\n".join(department_lines)
        return (
            "Classify the user's message using the department rules below. "
            f"Use {self._routing_config.fallback_department} when no other department "
            "clearly matches. You must call send_email exactly once with the selected "
            "department. Do not answer without calling the tool.\n\n"
            f"Departments:\n{departments}"
        )

    def _tool_schema(self) -> dict[str, Any]:
        department_ids = [
            department.id for department in self._routing_config.departments
        ]
        return {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Send the user's message to the selected department.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "department": {
                            "type": "string",
                            "description": "Configured department identifier.",
                            "enum": department_ids,
                        }
                    },
                    "required": ["department"],
                    "additionalProperties": False,
                },
            },
        }

    @staticmethod
    def _single_tool_call(
        tool_calls: Sequence[Message.ToolCall] | None,
    ) -> Message.ToolCall:
        if not tool_calls:
            raise AgentResponseError("Model did not call the email tool")
        if len(tool_calls) != 1:
            raise AgentResponseError("Model must call the email tool exactly once")

        tool_call = tool_calls[0]
        if tool_call.function.name != TOOL_NAME:
            raise AgentResponseError(
                f"Model called an unsupported tool: {tool_call.function.name}"
            )
        return tool_call

    def _department_argument(self, arguments: Mapping[str, Any]) -> str:
        if set(arguments) != {"department"}:
            raise AgentResponseError(
                "Email tool requires exactly one department argument"
            )

        department = arguments["department"]
        allowed_departments = {
            configured.id for configured in self._routing_config.departments
        }
        if not isinstance(department, str) or department not in allowed_departments:
            raise AgentResponseError(
                f"Model selected an unknown department: {department}"
            )
        return department
