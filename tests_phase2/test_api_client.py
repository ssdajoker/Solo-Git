from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from sologit.api.client import AbacusAPIError, AbacusClient, ChatResponse


@pytest.fixture
def client():
    return AbacusClient(api_key="test-key")


def make_response(**kwargs):
    response = Mock()
    for key, value in kwargs.items():
        setattr(response, key, value)
    return response


def test_resolve_deployment_requires_credentials(client):
    with pytest.raises(ValueError, match="requires deployment_id"):
        client._resolve_deployment(deployment=None, deployment_id=None, deployment_token=None)


def test_resolve_deployment_uses_registered_credentials(client):
    client.register_deployment("chat", "dep-123", "tok-456")
    deployment_id, deployment_token = client._resolve_deployment(
        deployment="chat", deployment_id=None, deployment_token=None
    )
    assert deployment_id == "dep-123"
    assert deployment_token == "tok-456"


def test_resolve_deployment_prefers_direct_credentials(client):
    client.register_deployment("chat", "dep-1", "tok-1")
    deployment_id, deployment_token = client._resolve_deployment(
        deployment="chat",
        deployment_id="override-id",
        deployment_token="override-token",
    )
    assert deployment_id == "override-id"
    assert deployment_token == "override-token"


def test_post_retries_and_succeeds(client):
    first = make_response(
        status_code=503,
        headers={"Retry-After": "0"},
        json=Mock(return_value={"success": True}),
        text="service unavailable",
    )
    second = make_response(
        status_code=200,
        headers={},
        json=Mock(return_value={"success": True, "data": {"value": 1}}),
    )
    with patch.object(client.session, "post", side_effect=[first, second]) as post, patch(
        "sologit.api.client.time.sleep"
    ) as sleep:
        payload = client._post("/chat", {"messages": []})

    assert payload["data"]["value"] == 1
    assert post.call_count == 2
    sleep.assert_called_once()


def test_post_invalid_json_raises_error(client):
    bad_response = make_response(
        status_code=200,
        headers={},
        json=Mock(side_effect=ValueError("bad json")),
        text="not-json",
    )
    with patch.object(client.session, "post", return_value=bad_response):
        with pytest.raises(AbacusAPIError, match="Invalid JSON"):
            client._post("/chat", {"messages": []})


def test_post_http_error_includes_snippet(client):
    response = make_response(status_code=500, headers={}, text="boom")
    with patch.object(client.session, "post", return_value=response):
        with pytest.raises(AbacusAPIError, match="500"):
            client._post("/chat", {})


def test_get_retry_delay_uses_header(client):
    response = SimpleNamespace(headers={"Retry-After": "1"})
    assert client._get_retry_delay(response, 0) == 1.0


def test_get_retry_delay_uses_backoff_when_header_missing(client):
    response = SimpleNamespace(headers={})
    with patch("sologit.api.client.time.sleep", autospec=True):
        delay = client._get_retry_delay(response, 2)
    assert 6 <= delay <= 6.5


def test_chat_completion_returns_simplified_payload(client):
    chat_response = ChatResponse(
        content="hello",
        model="gpt-4o",
        prompt_tokens=10,
        completion_tokens=20,
    )
    with patch.object(client, "chat", return_value=chat_response):
        payload = client.chat_completion([
            {"role": "user", "content": "hi"},
        ])

    assert payload["content"] == "hello"
    assert payload["usage"]["total_tokens"] == 30
    assert payload["cost_usd"] > 0
