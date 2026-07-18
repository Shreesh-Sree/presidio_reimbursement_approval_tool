"""Azure Communication Services Email delivery backend.

Used in production when AZURE_COMMUNICATION_CONNECTION_STRING is configured.
Falls back to SMTP (local MailHog) when absent.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

from azure.communication.email import EmailClient

logger = logging.getLogger("presidio.email")


class AzureEmailSender:
    """Send transactional emails through Azure Communication Services."""

    def __init__(self, connection_string: str, sender_address: str) -> None:
        self._client = EmailClient.from_connection_string(connection_string)
        self._sender = sender_address

    def send(self, message: EmailMessage) -> None:
        to_address = message["To"]
        subject = message["Subject"] or "Reimbursement Notification"
        body = message.get_content() if hasattr(message, "get_content") else str(message.get_payload())

        email_message = {
            "senderAddress": self._sender,
            "content": {
                "subject": subject,
                "plainText": body,
            },
            "recipients": {
                "to": [{"address": to_address}],
            },
        }

        poller = self._client.begin_send(email_message)
        result = poller.result()
        logger.info(
            "azure_email_sent",
            extra={
                "to": to_address,
                "message_id": result.get("id", "unknown"),
                "status": result.get("status", "unknown"),
            },
        )

    def close(self) -> None:
        pass
