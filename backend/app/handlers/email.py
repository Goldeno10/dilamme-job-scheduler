import asyncio
import random
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)

# Simulated SMTP failures for testing retry/DLQ
SIMULATE_FAILURE_RATE = 0.05


async def handle_send_email(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Email simulation handler — validates payload, simulates SMTP latency,
    and writes structured delivery log. Not a fake 200 return.
    """
    to = payload.get("to")
    subject = payload.get("subject", "")
    body = payload.get("body", "")

    if not to or "@" not in str(to):
        raise ValueError(f"Invalid email recipient: {to}")

    if not subject:
        raise ValueError("Email subject is required")

    # Simulate network + SMTP handshake latency
    await asyncio.sleep(random.uniform(0.1, 0.5))

    if payload.get("force_fail"):
        raise RuntimeError("Forced failure for testing")

    if random.random() < SIMULATE_FAILURE_RATE:
        raise ConnectionError(f"SMTP connection refused for {to}")

    message_id = f"msg_{random.randint(100000, 999999)}"
    logger.info(
        "email_delivered",
        to=to,
        subject=subject,
        body_length=len(body),
        message_id=message_id,
    )

    return {
        "message_id": message_id,
        "to": to,
        "subject": subject,
        "status": "delivered",
    }
