"""Async generation plus webhook verification.

Run the async demo:

    python examples/async_and_webhooks.py

The webhook helper is for your *server* — when you pass webhook_url to a
submit/generate call, verify the delivered payload like this in your handler.
"""

import asyncio

from bfl import AsyncBFL, verify_webhook


async def generate_async() -> None:
    async with AsyncBFL() as client:
        # Run several generations concurrently.
        prompts = [
            "a misty pine forest at dawn",
            "a coral reef teeming with fish, sun rays",
            "a lone lighthouse in a storm, dramatic",
        ]
        jobs = [await client.flux2.flex.submit(p, steps=30) for p in prompts]
        results = await asyncio.gather(*(job.wait() for job in jobs))
        for prompt, result in zip(prompts, results):
            print(f"{prompt!r} -> {result.url[:60]}...")


def handle_webhook(secret: str, received_secret: str | None) -> bool:
    """Example webhook handler check (framework-agnostic).

    BFL echoes your ``webhook_secret`` back in the ``X-Webhook-Secret`` header.
    Read that header off the incoming request and compare it in constant time.
    """
    if not verify_webhook(secret, received_secret):
        raise ValueError("Invalid webhook secret — reject this request.")
    print("Verified webhook — payload is trusted.")
    return True


if __name__ == "__main__":
    asyncio.run(generate_async())
