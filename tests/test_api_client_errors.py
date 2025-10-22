
"""Tests for the Abacus.ai API client error handling."""
import pytest
from unittest.mock import MagicMock, patch
from sologit.api.client import AbacusClient, AbacusAPIError
from sologit.config.manager import AbacusAPIConfig
import requests

@pytest.fixture
def api_config():
    """Fixture for AbacusAPIConfig."""
    return AbacusAPIConfig(endpoint="https://api.example.com", api_key="test_key")

@pytest.fixture
def client(api_config):
    """Fixture for AbacusClient."""
    return AbacusClient(api_config)

def test_timeout_scenario(client):
    """Test that the client handles a request timeout."""
    with patch.object(client.session, 'post', side_effect=requests.exceptions.Timeout):
        with pytest.raises(AbacusAPIError, match="Request to /test failed:"):
            client._post('/test', {})

def test_rate_limit_scenario(client):
    """Test that the client handles a 429 rate limit response."""
    with patch.object(client.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {'error': 'Rate limit exceeded'}
        mock_post.return_value = mock_response
        with pytest.raises(AbacusAPIError, match="HTTP 429 calling /test"):
            client._post('/test', {})

def test_auth_error_scenario(client):
    """Test that the client handles a 401 authentication error."""
    with patch.object(client.session, 'post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'error': 'Invalid API key'}
        mock_post.return_value = mock_response
        with pytest.raises(AbacusAPIError, match="HTTP 401 calling /test"):
            client._post('/test', {})

def test_network_failure_scenario(client):
    """Test that the client handles a network failure."""
    with patch.object(client.session, 'post', side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(AbacusAPIError, match="Request to /test failed:"):
            client._post('/test', {})

def test_retry_logic(client, mocker):
    """Test that the client retries on 503 errors."""
    mock_post = mocker.patch.object(client.session, 'post')
    mock_post.side_effect = [
        MagicMock(status_code=503, json=lambda: {'error': 'Service Unavailable'}),
        MagicMock(status_code=200, json=lambda: {'success': True})
    ]
    client._post('/test', {})
    assert mock_post.call_count == 2

def test_build_http_error(client):
    """Test the _build_http_error method."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {'error': 'Bad Request'}
    error = client._build_http_error('/test', mock_response)
    assert "HTTP 400 calling /test: Bad Request" in str(error)

def test_extract_error_message(client):
    """Test the _extract_error_message method."""
    assert "test" == client._extract_error_message({'error': 'test'})
    assert "test" == client._extract_error_message({'message': 'test'})
    assert "test" == client._extract_error_message({'detail': 'test'})

def test_extract_content(client):
    """Test the _extract_content method."""
    assert "test" == client._extract_content({'response': {'content': 'test'}})
    assert "test" == client._extract_content({'choices': [{'message': {'content': 'test'}}]})
    assert "test" == client._extract_content({'content': 'test'})

def test_extract_finish_reason(client):
    """Test the _extract_finish_reason method."""
    assert "test" == client._extract_finish_reason({'finishReason': 'test'})
    assert "test" == client._extract_finish_reason({'response': {'finishReason': 'test'}})

def test_extract_usage(client):
    """Test the _extract_usage method."""
    usage = client._extract_usage({'usage': {'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3}})
    assert usage['prompt_tokens'] == 1
    assert usage['completion_tokens'] == 2
    assert usage['total_tokens'] == 3

def test_test_connection_success(client, mocker):
    """Test the test_connection method successfully."""
    mock_post = mocker.patch.object(client, '_post')
    mock_post.return_value = {'success': True}
    assert client.test_connection() is True

def test_test_connection_failure(client, mocker):
    """Test the test_connection method with a failure."""
    mock_post = mocker.patch.object(client, '_post')
    mock_post.side_effect = AbacusAPIError
    assert client.test_connection() is False
