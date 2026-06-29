"""Tests for job lifecycle, result handling, and the high-level client."""

from __future__ import annotations

import pytest

from bfl._client import BFL
from bfl._exceptions import BFLContentModerated, BFLTaskError, BFLTimeoutError
from bfl._jobs import Job, Result, _interpret


def test_interpret_ready():
    ready, data = _interpret({"id": "t", "status": "Ready", "result": {"sample": "u"}})
    assert ready is True
    assert data["result"]["sample"] == "u"


def test_interpret_pending():
    ready, _ = _interpret({"id": "t", "status": "Pending"})
    assert ready is False


def test_interpret_content_moderated():
    with pytest.raises(BFLContentModerated) as exc:
        _interpret({"id": "t", "status": "Content Moderated"})
    assert exc.value.stage == "content"


def test_interpret_request_moderated():
    with pytest.raises(BFLContentModerated) as exc:
        _interpret({"id": "t", "status": "Request Moderated"})
    assert exc.value.stage == "request"


def test_interpret_error():
    with pytest.raises(BFLTaskError):
        _interpret({"id": "t", "status": "Error"})


def test_interpret_unknown_status_raises():
    """An unrecognized status must surface, not poll forever."""
    with pytest.raises(BFLTaskError) as exc:
        _interpret({"id": "t", "status": "Frobnicating"})
    assert exc.value.status == "Frobnicating"


def test_interpret_missing_status_raises():
    with pytest.raises(BFLTaskError):
        _interpret({"id": "t"})


def test_async_result_forbids_blocking_accessors():
    """A result from an async job must refuse blocking sync I/O."""
    from bfl._exceptions import BFLError

    result = Result(id="t", raw={"sample": "https://img/x.png"}, _async=True)
    # URL/metadata are fine (no I/O)...
    assert result.url == "https://img/x.png"
    # ...but blocking downloads are refused with a pointer to the async variant.
    with pytest.raises(BFLError, match="async"):
        result.save("/tmp/should-not-write.png")
    with pytest.raises(BFLError, match="async"):
        result.bytes()


def test_job_wait_polls_until_ready(client):
    transport = client._transport
    transport.queue(
        {"id": "abc", "polling_url": "/v1/get_result?id=abc", "cost": 5.0},  # submit
        {"id": "abc", "status": "Pending"},
        {"id": "abc", "status": "Pending"},
        {
            "id": "abc",
            "status": "Ready",
            "result": {"sample": "https://img/x.png", "seed": 7},
        },
    )
    job = client.flux2.pro.submit("a fox", width=1024, height=1024)
    assert isinstance(job, Job)
    assert job.cost == 5.0
    result = job.wait(poll_interval=0)
    assert isinstance(result, Result)
    assert result.url == "https://img/x.png"
    assert result.seed == 7


def test_job_wait_raises_on_moderation(client):
    client._transport.queue(
        {"id": "abc", "polling_url": "/v1/get_result?id=abc"},
        {"id": "abc", "status": "Content Moderated"},
    )
    job = client.flux2.pro.submit("a fox")
    with pytest.raises(BFLContentModerated):
        job.wait(poll_interval=0)


def test_job_wait_timeout(client):
    client._transport.queue(
        {"id": "abc", "polling_url": "/v1/get_result?id=abc"},
        {"id": "abc", "status": "Pending"},
    )
    job = client.flux2.pro.submit("a fox")
    with pytest.raises(BFLTimeoutError):
        job.wait(timeout=0, poll_interval=0)


def test_generate_convenience(client):
    client._transport.queue(
        {"id": "abc", "polling_url": "/v1/get_result?id=abc"},
        {"id": "abc", "status": "Ready", "result": {"sample": "https://img/y.png"}},
    )
    result = client.generate("a fox", poll_interval=0)
    assert result.url == "https://img/y.png"
    # default model is flux-2-pro
    submit_call = client._transport.calls[0]
    assert submit_call["url"] == "/v1/flux-2-pro"


def test_submit_records_correct_path(client):
    client._transport.queue({"id": "abc", "polling_url": "/v1/get_result?id=abc"})
    client.flux2.max.submit("a fox")
    assert client._transport.calls[0]["url"] == "/v1/flux-2-max"


def test_estimate_cost_rejects_non_flux2(client):
    from bfl._exceptions import BFLValidationError

    with pytest.raises(BFLValidationError):
        client.estimate_cost("flux-pro-1.1")


def test_credits(client):
    client._transport.queue({"credits": 1234.5})
    assert client.credits() == 1234.5


def test_unknown_model_raises():
    from bfl._exceptions import BFLValidationError

    c = BFL(api_key="bfl_" + "x" * 32)
    with pytest.raises(BFLValidationError):
        c.model("flux-9000")


def test_missing_api_key_raises(monkeypatch):
    from bfl._exceptions import BFLConfigError

    monkeypatch.delenv("BFL_API_KEY", raising=False)
    with pytest.raises(BFLConfigError):
        BFL()
