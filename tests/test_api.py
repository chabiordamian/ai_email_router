from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.agent import AgentResponseError, AgentResult
from app.main import app


def test_routes_valid_message() -> None:
    with patch(
        "app.main.RoutingAgent.route",
        new_callable=AsyncMock,
    ) as route:
        route.return_value = AgentResult(
            department="it",
            response="The message was sent to IT.",
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/messages",
                json={
                    "email": "jan.nowak@example.com",
                    "message": "  Nie działa firmowa sieć.  ",
                },
            )

    assert response.status_code == 200
    assert response.json() == {
        "department": "it",
        "response": "The message was sent to IT.",
    }
    route.assert_awaited_once_with(
        sender_email="jan.nowak@example.com",
        message="Nie działa firmowa sieć.",
    )


def test_rejects_invalid_request_before_calling_agent() -> None:
    with patch(
        "app.main.RoutingAgent.route",
        new_callable=AsyncMock,
    ) as route:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/messages",
                json={"email": "not-an-email", "message": "   "},
            )

    assert response.status_code == 422
    route.assert_not_awaited()


def test_returns_bad_gateway_for_invalid_model_decision() -> None:
    with patch(
        "app.main.RoutingAgent.route",
        new_callable=AsyncMock,
    ) as route:
        route.side_effect = AgentResponseError("Model did not call the email tool")
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/messages",
                json={
                    "email": "jan.nowak@example.com",
                    "message": "Test message",
                },
            )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "The model returned an invalid routing decision"
    }
