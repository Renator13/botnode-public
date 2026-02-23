from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .models import NotificationRouterInput, NotificationRouterOutput
from .security import is_safe_public_http_url, request_with_retries


class NotificationRouterEngine:
    def __init__(self, timeout_seconds: float = 10.0, user_agent: str = "notification-router-v1/0.1") -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    async def run(self, payload: NotificationRouterInput) -> NotificationRouterOutput:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if payload.channel == "email":
            provider_id = f"email-{uuid4().hex[:12]}"
            return NotificationRouterOutput(status="sent", provider_id=provider_id, timestamp=now)

        if not is_safe_public_http_url(payload.recipient):
            raise ValueError(f"recipient URL is not allowed (non-public or local): {payload.recipient}")

        body = {
            "channel": payload.channel,
            "subject": payload.subject,
            "message": payload.message_body,
            "attachments": payload.attachments,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

        response = await request_with_retries(
            method="POST",
            url=payload.recipient,
            headers=headers,
            json_payload=body,
            timeout_seconds=self._timeout_seconds,
            max_attempts=4,
        )

        status = "sent" if 200 <= response.status_code < 300 else "failed"
        provider_id = f"http-{response.status_code}-{uuid4().hex[:8]}"
        return NotificationRouterOutput(status=status, provider_id=provider_id, timestamp=now)
