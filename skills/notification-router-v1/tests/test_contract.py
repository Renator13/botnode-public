import asyncio

from notification_router_v1.engine import NotificationRouterEngine
from notification_router_v1.models import NotificationRouterInput


def test_email_channel_returns_sent_status() -> None:
    payload = NotificationRouterInput(channel="email", recipient="ops@example.com", message_body="Alert")
    output = asyncio.run(NotificationRouterEngine().run(payload))

    assert output.status == "sent"
    assert output.provider_id
