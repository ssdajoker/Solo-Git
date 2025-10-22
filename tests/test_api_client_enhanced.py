import json
from typing import Any, Dict, List

import pytest

from sologit.api.client import (
    AbacusAPIError,
    AbacusClient,
    ChatMessage,
)
from sologit.config.manager import AbacusAPIConfig


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "", headers: Dict[str, str] = None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON available")
        return self._payload

    def iter_lines(self):  # pragma: no cover - only used for streaming tests
        if isinstance(self._payload, list):
            for item in self._payload:
                yield item
        return iter(())


@pytest.fixture
def abacus_client():
    config = AbacusAPIConfig(endpoint="https://api.abacus.ai/api/v0", api_key="test-key")
    return AbacusClient(config)


def test_chat_uses_registered_credentials_and_parses_usage(monkeypatch, abacus_client):
    abacus_client.register_deployment('planning', 'dep-123', 'token-abc')
    captured: Dict[str, Any] = {}

    def fake_post(url, json=None, stream=False, timeout=60):
        captured['json'] = json
        captured['stream'] = stream
        payload = {
            'success': True,
            'model': 'abacus-planner',
            'response': {
                'content': json['messages'][0]['text'],
                'usage': {
                    'promptTokens': 12,
                    'completionTokens': 30,
                },
            },
        }
        return FakeResponse(200, payload)

    monkeypatch.setattr(abacus_client.session, 'post', fake_post)

    messages = [ChatMessage(role='user', content='{"title": "Plan"}')]
    response = abacus_client.chat(messages=messages, model='gpt-4o', deployment='planning')

    assert captured['json']['deploymentId'] == 'dep-123'
    assert captured['json']['deploymentToken'] == 'token-abc'
    assert response.model == 'abacus-planner'
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 30
    assert response.total_tokens == 42
    assert response.tokens_used == 42


def test_chat_raises_abacus_error(monkeypatch, abacus_client):
    def fake_post(url, json=None, stream=False, timeout=60):
        payload = {'error': {'message': 'Invalid token', 'code': 'bad_token'}}
        return FakeResponse(401, payload)

    monkeypatch.setattr(abacus_client.session, 'post', fake_post)

    messages = [ChatMessage(role='user', content='hello')]
    with pytest.raises(AbacusAPIError) as exc:
        abacus_client.chat(
            messages=messages,
            model='gpt-4o',
            deployment_id='dep',
            deployment_token='token',
        )


def test_chat_rate_limit_retries_and_succeeds(monkeypatch, abacus_client):
    """Verify that a 429 rate limit error triggers a retry."""
    call_count = 0

    def fake_post_rate_limit(url, json=None, stream=False, timeout=60):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResponse(429, text="Rate limit exceeded")

        payload = {
            'success': True,
            'model': 'abacus-planner',
            'response': {
                'content': 'Success on retry',
                'usage': {'promptTokens': 1, 'completionTokens': 3},
            },
        }
        return FakeResponse(200, payload)

    monkeypatch.setattr(abacus_client.session, 'post', fake_post_rate_limit)
    monkeypatch.setattr('time.sleep', lambda s: None)

    messages = [ChatMessage(role='user', content='hello')]
    response = abacus_client.chat(
        messages=messages,
        model='gpt-4o',
        deployment_id='dep',
        deployment_token='token',
    )

    assert call_count == 2
    assert response.content == 'Success on retry'


def test_chat_auth_error_does_not_retry(monkeypatch, abacus_client):
    """Verify that a 401 auth error is not retried."""
    call_count = 0

    def fake_post_auth_error(url, json=None, stream=False, timeout=60):
        nonlocal call_count
        call_count += 1
        return FakeResponse(401, text="Unauthorized")

    monkeypatch.setattr(abacus_client.session, 'post', fake_post_auth_error)

    messages = [ChatMessage(role='user', content='hello')]
    with pytest.raises(AbacusAPIError, match="HTTP 401"):
        abacus_client.chat(
            messages=messages,
            model='gpt-4o',
            deployment_id='dep',
            deployment_token='token',
        )

    assert call_count == 1  # Should not retry on auth error


def test_chat_network_error_raises_abacus_error(monkeypatch, abacus_client):
    """Verify that a network error raises AbacusAPIError."""
    import requests

    def fake_post_network_error(url, json=None, stream=False, timeout=60):
        raise requests.exceptions.ConnectionError("Network is unreachable")

    monkeypatch.setattr(abacus_client.session, 'post', fake_post_network_error)

    messages = [ChatMessage(role='user', content='hello')]
    with pytest.raises(AbacusAPIError, match="Network is unreachable"):
        abacus_client.chat(
            messages=messages,
            model='gpt-4o',
            deployment_id='dep',
            deployment_token='token',
        )


def test_retry_logic_with_exponential_backoff(monkeypatch, abacus_client):
    """Verify that a 503 error triggers retries with exponential backoff."""
    call_count = 0
    retry_delays = []

    def fake_post_503(url, json=None, stream=False, timeout=60):
        nonlocal call_count
        call_count += 1
        return FakeResponse(503, text="Service Unavailable")

    def fake_get_retry_delay(response, attempt):
        delay = 0.01 * (2 ** attempt)  # Exponential backoff
        retry_delays.append(delay)
        return delay

    monkeypatch.setattr(abacus_client.session, 'post', fake_post_503)
    monkeypatch.setattr(abacus_client, '_get_retry_delay', fake_get_retry_delay)
    monkeypatch.setattr('time.sleep', lambda s: None)

    messages = [ChatMessage(role='user', content='hello')]
    with pytest.raises(AbacusAPIError, match="HTTP 503"):
        abacus_client.chat(
            messages=messages,
            model='gpt-4o',
            deployment_id='dep',
            deployment_token='token',
        )

    assert call_count == 3
    assert len(retry_delays) == 2  # 2 delays for 3 attempts
    assert retry_delays[0] == 0.01
    assert retry_delays[1] == 0.02


def test_stream_chat_yields_chunks_and_returns_response(monkeypatch, abacus_client):
    stream_events: List[bytes] = [
        b'data: {"content": "Hello "}',
        b'data: {"content": "world", "usage": {"completionTokens": 2, "promptTokens": 1}}',
        b'data: [DONE]',
    ]

    class StreamResponse(FakeResponse):
        def __init__(self):
            super().__init__(200, stream_events)

    def fake_post(url, json=None, stream=False, timeout=60):
        assert stream is True
        return StreamResponse()

    monkeypatch.setattr(abacus_client.session, 'post', fake_post)

    generator = abacus_client.stream_chat(
        messages=[ChatMessage(role='user', content='hello')],
        model='gpt-4o',
        deployment_id='dep',
        deployment_token='token',
    )

    chunks: List[str] = []
    try:
        while True:
            chunks.append(next(generator))
    except StopIteration as stop:
        final_response = stop.value

    assert ''.join(chunks) == 'Hello world'
    assert final_response.completion_tokens == 2
    assert final_response.prompt_tokens == 1
    assert final_response.total_tokens == 3  # prompt (1) + completion (2)


def test_chat_timeout_raises_abacus_error(monkeypatch, abacus_client):
    """Verify that a client-side timeout raises AbacusAPIError."""
    import requests

    def fake_post_timeout(url, json=None, stream=False, timeout=60):
        raise requests.exceptions.Timeout("Connection timed out")

    monkeypatch.setattr(abacus_client.session, 'post', fake_post_timeout)

    messages = [ChatMessage(role='user', content='hello')]
    with pytest.raises(AbacusAPIError, match="Request to .* failed: .*"):
        abacus_client.chat(
            messages=messages,
            model='gpt-4o',
            deployment_id='dep',
            deployment_token='token',
        )
