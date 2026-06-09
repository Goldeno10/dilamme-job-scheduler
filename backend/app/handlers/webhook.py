import asyncio
import hashlib
import hmac
import json
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


async def handle_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Webhook delivery handler — signs payload and simulates HTTP POST."""
    url = payload.get("url")
    data = payload.get("data", {})
    secret = payload.get("secret", "webhook-secret")

    if not url:
        raise ValueError("Webhook URL is required")

    body = json.dumps(data, sort_keys=True)
    # HMAC is a hash-based message authentication code that is used to verify the integrity of the message.
    # It is a symmetric key algorithm that uses a shared secret key to sign the message.
    # The secret key is used to sign the message and the message is signed using the secret key.
    # The signature is then verified using the secret key.
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    await asyncio.sleep(0.2)

    if payload.get("force_fail"):
        raise RuntimeError("Webhook delivery failed")

    logger.info("webhook_delivered", url=url, signature=signature[:16], body_size=len(body))

    return {
        "url": url,
        "status_code": 200,
        "signature": signature,
    }
