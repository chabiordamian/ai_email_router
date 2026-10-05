from email.message import EmailMessage

import aiosmtplib

from app.routing_config import RoutingConfig
from app.settings import Settings


class EmailTool:
    def __init__(
        self,
        *,
        sender_email: str,
        message: str,
        routing_config: RoutingConfig,
        settings: Settings,
    ) -> None:
        self._sender_email = sender_email
        self._message = message
        self._routing_config = routing_config
        self._settings = settings

    async def send_email(self, department: str) -> str:
        """Send the request to a configured department.

        Args:
            department: Department identifier from the routing configuration.
        """
        recipient = self._recipient_for(department)
        email = EmailMessage()
        email["From"] = self._settings.email_from
        email["To"] = recipient
        email["Reply-To"] = self._sender_email
        email["Subject"] = f"New request for {department}"
        email.set_content(self._message)

        await aiosmtplib.send(
            email,
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            timeout=self._settings.smtp_timeout_seconds,
        )
        return f"Message sent to {department}"

    def _recipient_for(self, department_id: str) -> str:
        for department in self._routing_config.departments:
            if department.id == department_id:
                return str(department.email)

        raise ValueError(f"Unknown department: {department_id}")
