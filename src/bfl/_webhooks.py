"""Verify the authenticity of BFL completion webhooks.

When you pass ``webhook_url`` (and optionally ``webhook_secret``) to a
generation request, the API POSTs the finished task payload to your endpoint.
If you supplied a secret, the request carries it back **verbatim** in the
``X-Webhook-Secret`` header. Your handler should confirm that header matches
the secret you chose before trusting the payload.

This is a shared-secret check, not a body signature — so it does not depend on
the exact bytes of the delivered JSON.

Example (framework-agnostic)::

    from bfl import verify_webhook, WEBHOOK_SECRET_HEADER

    def handle(request):
        received = request.headers.get(WEBHOOK_SECRET_HEADER)
        if not verify_webhook(my_secret, received):
            abort(401)
        payload = request.json()  # trusted
"""

from __future__ import annotations

import hmac

from ._exceptions import BFLValidationError

#: HTTP header the BFL API uses to echo your webhook secret back to you.
WEBHOOK_SECRET_HEADER = "X-Webhook-Secret"


def verify_webhook(secret: str, received_secret: str | None) -> bool:
    """Check a delivered webhook against your expected secret, in constant time.

    Args:
        secret: The ``webhook_secret`` you supplied when submitting the task.
        received_secret: The value of the incoming ``X-Webhook-Secret`` header
            (``None`` if the header was absent).

    Returns:
        ``True`` if the header is present and matches ``secret``; ``False``
        otherwise (including when the header is missing).

    Raises:
        BFLValidationError: If ``secret`` is empty — you must configure the
            same secret you sent to the API.
    """
    if not secret:
        raise BFLValidationError(
            "Cannot verify a webhook without the secret you submitted. Pass the "
            "same `webhook_secret` you sent to the generation request."
        )
    if not received_secret:
        return False
    # Compare as bytes: hmac.compare_digest raises TypeError on str operands
    # that contain non-ASCII code points, which would crash an otherwise valid
    # verification call inside the user's webhook handler.
    return hmac.compare_digest(secret.encode("utf-8"), received_secret.encode("utf-8"))
