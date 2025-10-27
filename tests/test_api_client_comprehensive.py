"""Comprehensive tests for the Abacus.ai API client error handling - 100% coverage target."""
import json
import pytest
from unittest.mock import MagicMock, patch, Mock
from sologit.api.client import (
    AbacusClient, 
    AbacusAPIError, 
    ChatMessage, 
    ChatResponse
)
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


# ==================== Test ChatResponse __post_init__ ====================
def test_chat_response_post_init_calculates_total_tokens():
    """Test ChatResponse calculates total_tokens from prompt and completion tokens."""
    response = ChatResponse(
        content="test",
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=0  # Should be calculated
    )
    assert response.total_tokens == 30
    assert response.tokens_used == 30


def test_chat_response_post_init_sets_tokens_used():
    """Test ChatResponse sets tokens_used from total_tokens."""
    response = ChatResponse(
        content="test",
        model="gpt-4",
        total_tokens=50,
        tokens_used=0  # Should be set from total_tokens
    )
    assert response.tokens_used == 50


# ==================== Test Client Initialization ====================
def test_client_init_with_v1_endpoint():
    """Test client initialization adjusts /v1 endpoint to /api/v0."""
    config = AbacusAPIConfig(
        endpoint="https://api.example.com/v1", 
        api_key="test_key"
    )
    client = AbacusClient(config)
    assert client.endpoint == "https://api.example.com/api/v0"


def test_client_init_without_api_v0_suffix():
    """Test client initialization adds /api/v0 suffix if missing."""
    config = AbacusAPIConfig(
        endpoint="https://api.example.com", 
        api_key="test_key"
    )
    client = AbacusClient(config)
    assert client.endpoint == "https://api.example.com/api/v0"


def test_client_init_with_correct_endpoint():
    """Test client initialization keeps correct endpoint."""
    config = AbacusAPIConfig(
        endpoint="https://api.example.com/api/v0", 
        api_key="test_key"
    )
    client = AbacusClient(config)
    assert client.endpoint == "https://api.example.com/api/v0"


# ==================== Test Deployment Management ====================
def test_register_deployment(client):
    """Test registering deployment credentials."""
    client.register_deployment("test_deployment", "dep-123", "token-abc")
    assert "test_deployment" in client.deployments
    assert client.deployments["test_deployment"]["deployment_id"] == "dep-123"
    assert client.deployments["test_deployment"]["deployment_token"] == "token-abc"


def test_get_registered_deployment(client):
    """Test retrieving registered deployment credentials."""
    client.register_deployment("test_deployment", "dep-123", "token-abc")
    deployment = client.get_registered_deployment("test_deployment")
    assert deployment is not None
    assert deployment["deployment_id"] == "dep-123"
    assert deployment["deployment_token"] == "token-abc"


def test_get_registered_deployment_not_found(client):
    """Test retrieving non-existent deployment returns None."""
    deployment = client.get_registered_deployment("non_existent")
    assert deployment is None


def test_clear_deployment(client):
    """Test clearing deployment credentials."""
    client.register_deployment("test_deployment", "dep-123", "token-abc")
    client.clear_deployment("test_deployment")
    assert "test_deployment" not in client.deployments


def test_clear_deployment_not_exists(client):
    """Test clearing non-existent deployment doesn't raise error."""
    client.clear_deployment("non_existent")  # Should not raise


# ==================== Test _resolve_deployment ====================
def test_resolve_deployment_with_direct_credentials(client):
    """Test resolving deployment with direct deployment_id and deployment_token."""
    dep_id, dep_token = client._resolve_deployment(
        deployment=None,
        deployment_id="dep-123",
        deployment_token="token-abc"
    )
    assert dep_id == "dep-123"
    assert dep_token == "token-abc"


def test_resolve_deployment_with_registration(client):
    """Test resolving deployment registers credentials when deployment name provided."""
    dep_id, dep_token = client._resolve_deployment(
        deployment="test_deployment",
        deployment_id="dep-123",
        deployment_token="token-abc"
    )
    assert dep_id == "dep-123"
    assert dep_token == "token-abc"
    assert "test_deployment" in client.deployments


def test_resolve_deployment_from_registered(client):
    """Test resolving deployment from registered credentials."""
    client.register_deployment("test_deployment", "dep-123", "token-abc")
    dep_id, dep_token = client._resolve_deployment(
        deployment="test_deployment",
        deployment_id=None,
        deployment_token=None
    )
    assert dep_id == "dep-123"
    assert dep_token == "token-abc"


def test_resolve_deployment_not_registered_raises_error(client):
    """Test resolving unregistered deployment raises ValueError."""
    with pytest.raises(ValueError, match="No credentials registered"):
        client._resolve_deployment(
            deployment="non_existent",
            deployment_id=None,
            deployment_token=None
        )


def test_resolve_deployment_missing_credentials_raises_error(client):
    """Test resolving deployment without credentials raises ValueError."""
    with pytest.raises(ValueError, match="requires deployment_id and deployment_token"):
        client._resolve_deployment(
            deployment=None,
            deployment_id=None,
            deployment_token=None
        )


def test_resolve_deployment_partial_credentials_raises_error(client):
    """Test resolving deployment with only deployment_id raises ValueError."""
    with pytest.raises(ValueError, match="requires deployment_id and deployment_token"):
        client._resolve_deployment(
            deployment=None,
            deployment_id="dep-123",
            deployment_token=None
        )


# ==================== Test _post Error Handling ====================
def test_post_stream_returns_response(client):
    """Test _post with stream=True returns response object."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch.object(client.session, 'post', return_value=mock_response):
        result = client._post('/test', {}, stream=True)
        assert result == mock_response


def test_post_invalid_json_response_raises_error(client):
    """Test _post with invalid JSON response raises AbacusAPIError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Invalid response text"
    
    with patch.object(client.session, 'post', return_value=mock_response):
        with pytest.raises(AbacusAPIError, match="Invalid JSON response"):
            client._post('/test', {})


def test_post_success_false_raises_error(client):
    """Test _post with success=False in response raises AbacusAPIError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': False,
        'error': 'Operation failed'
    }
    
    with patch.object(client.session, 'post', return_value=mock_response):
        with pytest.raises(AbacusAPIError, match="Operation failed"):
            client._post('/test', {})


def test_post_429_retries_with_retry_after_header(client):
    """Test _post retries on 429 with Retry-After header."""
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "2"}
    
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {'success': True, 'data': 'test'}
    
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_response_429
        return mock_response_200
    
    with patch.object(client.session, 'post', side_effect=side_effect):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client._post('/test', {})
            assert result['data'] == 'test'
            assert call_count == 2


def test_post_503_retries_with_exponential_backoff(client):
    """Test _post retries on 503 with exponential backoff."""
    mock_response_503 = MagicMock()
    mock_response_503.status_code = 503
    mock_response_503.json.return_value = {'error': 'Service Unavailable'}
    
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {'success': True, 'data': 'test'}
    
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return mock_response_503
        return mock_response_200
    
    with patch.object(client.session, 'post', side_effect=side_effect):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client._post('/test', {})
            assert result['data'] == 'test'
            assert call_count == 2


def test_post_max_retries_exceeded_raises_error(client):
    """Test _post raises error after max retries exceeded."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json.return_value = {'error': 'Service Unavailable'}
    
    with patch.object(client.session, 'post', return_value=mock_response):
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(AbacusAPIError, match="HTTP 503"):
                client._post('/test', {}, max_retries=3)


# ==================== Test _get_retry_delay ====================
def test_get_retry_delay_with_retry_after_header(client):
    """Test _get_retry_delay uses Retry-After header."""
    mock_response = MagicMock()
    mock_response.headers = {"Retry-After": "5.0"}
    
    delay = client._get_retry_delay(mock_response, 0)
    assert delay == 5.0


def test_get_retry_delay_with_invalid_retry_after_header(client):
    """Test _get_retry_delay handles invalid Retry-After header."""
    mock_response = MagicMock()
    mock_response.headers = {"Retry-After": "invalid"}
    
    delay = client._get_retry_delay(mock_response, 0)
    # Should fall back to exponential backoff
    assert delay >= 1.5  # base_delay


def test_get_retry_delay_exponential_backoff(client):
    """Test _get_retry_delay uses exponential backoff."""
    mock_response = MagicMock()
    mock_response.headers = {}
    
    delay_0 = client._get_retry_delay(mock_response, 0)
    delay_1 = client._get_retry_delay(mock_response, 1)
    delay_2 = client._get_retry_delay(mock_response, 2)
    
    # Delays should increase exponentially (with some jitter)
    assert delay_0 >= 1.5  # base_delay
    assert delay_1 >= 3.0  # base_delay * 2^1
    assert delay_2 >= 6.0  # base_delay * 2^2


def test_get_retry_delay_max_delay_cap(client):
    """Test _get_retry_delay caps at max_delay."""
    mock_response = MagicMock()
    mock_response.headers = {}
    
    delay = client._get_retry_delay(mock_response, 10)  # Large attempt number
    assert delay <= 30.5  # max_delay (30) + max jitter (0.5)


# ==================== Test _build_http_error ====================
def test_build_http_error_with_json_error(client):
    """Test _build_http_error with JSON error payload."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {'error': 'Bad Request'}
    
    error = client._build_http_error('/test', mock_response)
    assert "HTTP 400 calling /test: Bad Request" in str(error)


def test_build_http_error_with_text_snippet(client):
    """Test _build_http_error with text response."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Internal Server Error"
    
    error = client._build_http_error('/test', mock_response)
    assert "HTTP 500 calling /test: Internal Server Error" in str(error)


def test_build_http_error_with_empty_text(client):
    """Test _build_http_error with empty text response."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = ""
    
    error = client._build_http_error('/test', mock_response)
    assert "HTTP 404 calling /test" in str(error)


# ==================== Test _extract_error_message ====================
def test_extract_error_message_from_string(client):
    """Test _extract_error_message with string input."""
    assert client._extract_error_message("Error message") == "Error message"


def test_extract_error_message_from_non_dict(client):
    """Test _extract_error_message with non-dict input."""
    assert "42" in client._extract_error_message(42)


def test_extract_error_message_from_error_string(client):
    """Test _extract_error_message with error as string."""
    assert client._extract_error_message({'error': 'Test error'}) == 'Test error'


def test_extract_error_message_from_error_dict(client):
    """Test _extract_error_message with error as dict."""
    error_dict = {
        'error': {
            'message': 'Test message',
            'code': 'TEST_CODE',
            'type': 'TestError',
            'details': 'Test details'
        }
    }
    result = client._extract_error_message(error_dict)
    assert 'Test message' in result
    assert 'TEST_CODE' in result


def test_extract_error_message_from_message_field(client):
    """Test _extract_error_message from message field."""
    assert client._extract_error_message({'message': 'Test message'}) == 'Test message'


def test_extract_error_message_from_detail_field(client):
    """Test _extract_error_message from detail field."""
    assert client._extract_error_message({'detail': 'Test detail'}) == 'Test detail'


def test_extract_error_message_from_errorMessage_field(client):
    """Test _extract_error_message from errorMessage field."""
    assert client._extract_error_message({'errorMessage': 'Test error'}) == 'Test error'


def test_extract_error_message_from_error_description_field(client):
    """Test _extract_error_message from error_description field."""
    assert client._extract_error_message({'error_description': 'Description'}) == 'Description'


def test_extract_error_message_from_errors_list_dict(client):
    """Test _extract_error_message from errors list with dict."""
    errors = {
        'errors': [
            {'message': 'First error', 'detail': 'First detail'}
        ]
    }
    result = client._extract_error_message(errors)
    assert 'First error' in result or 'First detail' in result


def test_extract_error_message_from_errors_list_string(client):
    """Test _extract_error_message from errors list with string."""
    errors = {'errors': ['First error']}
    result = client._extract_error_message(errors)
    assert 'First error' in result


def test_extract_error_message_fallback_to_repr(client):
    """Test _extract_error_message falls back to repr."""
    result = client._extract_error_message({'unknown_field': 'value'})
    assert 'unknown_field' in result


# ==================== Test _extract_content ====================
def test_extract_content_from_non_dict(client):
    """Test _extract_content with non-dict input."""
    assert client._extract_content("not a dict") == ''


def test_extract_content_from_response_content(client):
    """Test _extract_content from response.content field."""
    payload = {'response': {'content': 'Test content'}}
    assert client._extract_content(payload) == 'Test content'


def test_extract_content_from_response_text(client):
    """Test _extract_content from response.text field."""
    payload = {'response': {'text': 'Test text'}}
    assert client._extract_content(payload) == 'Test text'


def test_extract_content_from_response_message(client):
    """Test _extract_content from response.message field."""
    payload = {'response': {'message': 'Test message'}}
    assert client._extract_content(payload) == 'Test message'


def test_extract_content_from_response_output(client):
    """Test _extract_content from response.output field."""
    payload = {'response': {'output': 'Test output'}}
    assert client._extract_content(payload) == 'Test output'


def test_extract_content_from_response_string(client):
    """Test _extract_content from response as string."""
    payload = {'response': 'String response'}
    assert client._extract_content(payload) == 'String response'


def test_extract_content_from_choices_message(client):
    """Test _extract_content from choices[0].message.content."""
    payload = {
        'choices': [
            {'message': {'content': 'Choice content'}}
        ]
    }
    assert client._extract_content(payload) == 'Choice content'


def test_extract_content_from_choices_content(client):
    """Test _extract_content from choices[0].content."""
    payload = {
        'choices': [
            {'content': 'Direct content'}
        ]
    }
    assert client._extract_content(payload) == 'Direct content'


def test_extract_content_from_choices_text(client):
    """Test _extract_content from choices[0].text."""
    payload = {
        'choices': [
            {'text': 'Choice text'}
        ]
    }
    assert client._extract_content(payload) == 'Choice text'


def test_extract_content_from_top_level(client):
    """Test _extract_content from top-level fields."""
    assert client._extract_content({'content': 'Top level'}) == 'Top level'
    assert client._extract_content({'text': 'Top text'}) == 'Top text'
    assert client._extract_content({'message': 'Top message'}) == 'Top message'
    assert client._extract_content({'output': 'Top output'}) == 'Top output'


def test_extract_content_empty_fallback(client):
    """Test _extract_content returns empty string when no content found."""
    assert client._extract_content({'unknown': 'data'}) == ''


# ==================== Test _extract_finish_reason ====================
def test_extract_finish_reason_from_non_dict(client):
    """Test _extract_finish_reason with non-dict input."""
    assert client._extract_finish_reason("not a dict") == 'stop'


def test_extract_finish_reason_from_finishReason(client):
    """Test _extract_finish_reason from finishReason field."""
    assert client._extract_finish_reason({'finishReason': 'length'}) == 'length'


def test_extract_finish_reason_from_finish_reason(client):
    """Test _extract_finish_reason from finish_reason field."""
    assert client._extract_finish_reason({'finish_reason': 'stop'}) == 'stop'


def test_extract_finish_reason_from_finish(client):
    """Test _extract_finish_reason from finish field."""
    assert client._extract_finish_reason({'finish': 'complete'}) == 'complete'


def test_extract_finish_reason_from_status(client):
    """Test _extract_finish_reason from status field."""
    assert client._extract_finish_reason({'status': 'done'}) == 'done'


def test_extract_finish_reason_from_response(client):
    """Test _extract_finish_reason from response.finishReason."""
    payload = {'response': {'finishReason': 'length'}}
    assert client._extract_finish_reason(payload) == 'length'


def test_extract_finish_reason_from_response_finish_reason(client):
    """Test _extract_finish_reason from response.finish_reason."""
    payload = {'response': {'finish_reason': 'stop'}}
    assert client._extract_finish_reason(payload) == 'stop'


def test_extract_finish_reason_default(client):
    """Test _extract_finish_reason returns default 'stop'."""
    assert client._extract_finish_reason({}) == 'stop'


# ==================== Test _extract_usage ====================
def test_extract_usage_from_usage_dict(client):
    """Test _extract_usage from usage dict."""
    payload = {
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 200,
            'total_tokens': 300
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 100
    assert usage['completion_tokens'] == 200
    assert usage['total_tokens'] == 300


def test_extract_usage_from_camelCase(client):
    """Test _extract_usage from camelCase fields."""
    payload = {
        'usage': {
            'promptTokens': 50,
            'completionTokens': 150,
            'totalTokens': 200
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 50
    assert usage['completion_tokens'] == 150
    assert usage['total_tokens'] == 200


def test_extract_usage_from_token_count_fields(client):
    """Test _extract_usage from token_count fields."""
    payload = {
        'usage': {
            'prompt_token_count': 30,
            'completion_token_count': 70
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 30
    assert usage['completion_tokens'] == 70


def test_extract_usage_from_tokensUsed(client):
    """Test _extract_usage from tokensUsed field."""
    payload = {
        'usage': {
            'tokensUsed': 250
        }
    }
    usage = client._extract_usage(payload)
    assert usage['total_tokens'] == 250


def test_extract_usage_from_tokens_used(client):
    """Test _extract_usage from tokens_used field."""
    payload = {
        'usage': {
            'tokens_used': 275
        }
    }
    usage = client._extract_usage(payload)
    assert usage['total_tokens'] == 275


def test_extract_usage_from_response_usage(client):
    """Test _extract_usage from response.usage."""
    payload = {
        'response': {
            'usage': {
                'prompt_tokens': 40,
                'completion_tokens': 60
            }
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 40
    assert usage['completion_tokens'] == 60


def test_extract_usage_from_response_direct(client):
    """Test _extract_usage from response fields directly."""
    payload = {
        'response': {
            'promptTokens': 25,
            'completionTokens': 75
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 25
    assert usage['completion_tokens'] == 75


def test_extract_usage_from_top_level(client):
    """Test _extract_usage from top-level fields."""
    payload = {
        'promptTokens': 15,
        'completionTokens': 35
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 15
    assert usage['completion_tokens'] == 35


def test_extract_usage_calculates_total(client):
    """Test _extract_usage calculates total from prompt + completion."""
    payload = {
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 150
        }
    }
    usage = client._extract_usage(payload)
    assert usage['total_tokens'] == 250


def test_extract_usage_safe_int_handles_invalid(client):
    """Test _extract_usage handles invalid token values."""
    payload = {
        'usage': {
            'prompt_tokens': 'invalid',
            'completion_tokens': None,
            'total_tokens': 100
        }
    }
    usage = client._extract_usage(payload)
    assert usage['prompt_tokens'] == 0
    assert usage['completion_tokens'] == 0
    assert usage['total_tokens'] == 100


# ==================== Test _build_chat_response ====================
def test_build_chat_response_complete(client):
    """Test _build_chat_response with complete payload."""
    payload = {
        'model': 'gpt-4',
        'response': {
            'content': 'Test response',
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 20
            }
        },
        'finishReason': 'stop'
    }
    response = client._build_chat_response(payload, 'fallback-model')
    assert response.model == 'gpt-4'
    assert response.content == 'Test response'
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 20
    assert response.total_tokens == 30
    assert response.finish_reason == 'stop'


def test_build_chat_response_uses_model_hint(client):
    """Test _build_chat_response uses model_hint as fallback."""
    payload = {
        'response': {
            'content': 'Test response'
        }
    }
    response = client._build_chat_response(payload, 'fallback-model')
    assert response.model == 'fallback-model'


def test_build_chat_response_extracts_model_from_response(client):
    """Test _build_chat_response extracts model from response object."""
    payload = {
        'response': {
            'model': 'response-model',
            'content': 'Test response'
        }
    }
    response = client._build_chat_response(payload, 'fallback-model')
    assert response.model == 'response-model'


# ==================== Test chat() method ====================
def test_chat_with_deployment_name(client):
    """Test chat() with deployment name."""
    client.register_deployment('test_dep', 'dep-123', 'token-abc')
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'model': 'gpt-4',
        'response': {
            'content': 'Hello',
            'usage': {'prompt_tokens': 5, 'completion_tokens': 10}
        }
    }
    
    with patch.object(client.session, 'post', return_value=mock_response):
        messages = [ChatMessage(role='user', content='Test')]
        response = client.chat(
            messages=messages,
            model='gpt-4',
            deployment='test_dep'
        )
        assert response.content == 'Hello'
        assert response.model == 'gpt-4'


def test_chat_with_custom_parameters(client):
    """Test chat() with custom max_tokens and temperature."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'response': {'content': 'Response'}
    }
    
    captured_payload = {}
    def capture_post(url, json=None, **kwargs):
        captured_payload.update(json)
        return mock_response
    
    with patch.object(client.session, 'post', side_effect=capture_post):
        messages = [ChatMessage(role='user', content='Test')]
        client.chat(
            messages=messages,
            model='gpt-4',
            max_tokens=4096,
            temperature=0.7,
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        assert captured_payload['maxTokens'] == 4096
        assert captured_payload['temperature'] == 0.7


def test_chat_with_kwargs(client):
    """Test chat() passes additional kwargs to payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'response': {'content': 'Response'}
    }
    
    captured_payload = {}
    def capture_post(url, json=None, **kwargs):
        captured_payload.update(json)
        return mock_response
    
    with patch.object(client.session, 'post', side_effect=capture_post):
        messages = [ChatMessage(role='user', content='Test')]
        client.chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc',
            custom_param='custom_value'
        )
        assert captured_payload['custom_param'] == 'custom_value'


# ==================== Test stream_chat() method ====================
def test_stream_chat_yields_chunks(client):
    """Test stream_chat() yields content chunks."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'data: {"response": {"content": "Hello "}}'
            yield b'data: {"response": {"content": "world"}}'
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        chunks = []
        try:
            while True:
                chunks.append(next(generator))
        except StopIteration as e:
            final_response = e.value
        
        assert ''.join(chunks) == 'Hello world'
        assert isinstance(final_response, ChatResponse)


def test_stream_chat_handles_empty_lines(client):
    """Test stream_chat() skips empty lines."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b''
            yield b'data: {"response": {"content": "Test"}}'
            yield b''
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        chunks = []
        try:
            while True:
                chunks.append(next(generator))
        except StopIteration:
            pass
        
        assert ''.join(chunks) == 'Test'


def test_stream_chat_handles_non_data_lines(client):
    """Test stream_chat() skips lines without 'data:' prefix."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'comment: This is a comment'
            yield b'data: {"response": {"content": "Test"}}'
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        chunks = []
        try:
            while True:
                chunks.append(next(generator))
        except StopIteration:
            pass
        
        assert ''.join(chunks) == 'Test'


def test_stream_chat_handles_invalid_json(client):
    """Test stream_chat() skips lines with invalid JSON."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'data: invalid json'
            yield b'data: {"response": {"content": "Test"}}'
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        chunks = []
        try:
            while True:
                chunks.append(next(generator))
        except StopIteration:
            pass
        
        assert ''.join(chunks) == 'Test'


def test_stream_chat_raises_on_error_event(client):
    """Test stream_chat() raises error on error event."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'data: {"event": "error", "error": "Stream error"}'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        with pytest.raises(AbacusAPIError, match="Stream error"):
            next(generator)


def test_stream_chat_builds_final_response(client):
    """Test stream_chat() builds final response with combined content."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'data: {"content": "Part1"}'
            yield b'data: {"content": "Part2", "usage": {"promptTokens": 5, "completionTokens": 10}}'
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        try:
            while True:
                next(generator)
        except StopIteration as e:
            final_response = e.value
        
        assert final_response.content == 'Part1Part2'
        assert final_response.prompt_tokens == 5
        assert final_response.completion_tokens == 10


def test_stream_chat_handles_empty_payload(client):
    """Test stream_chat() handles empty final payload."""
    class FakeStreamResponse:
        status_code = 200
        def iter_lines(self):
            yield b'data: [DONE]'
    
    with patch.object(client.session, 'post', return_value=FakeStreamResponse()):
        messages = [ChatMessage(role='user', content='Test')]
        generator = client.stream_chat(
            messages=messages,
            model='gpt-4',
            deployment_id='dep-123',
            deployment_token='token-abc'
        )
        
        try:
            while True:
                next(generator)
        except StopIteration as e:
            final_response = e.value
        
        assert final_response.content == ''


# ==================== Test get_usage_summary() ====================
def test_get_usage_summary_success(client):
    """Test get_usage_summary() returns usage data."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'success': True,
        'usageSummary': {
            'totalTokens': 10000,
            'totalCost': 5.50
        }
    }
    
    with patch.object(client.session, 'post', return_value=mock_response):
        summary = client.get_usage_summary()
        assert summary['totalTokens'] == 10000
        assert summary['totalCost'] == 5.50


def test_get_usage_summary_empty_response(client):
    """Test get_usage_summary() handles missing usageSummary."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'success': True}
    
    with patch.object(client.session, 'post', return_value=mock_response):
        summary = client.get_usage_summary()
        assert summary == {}


# ==================== Test Additional Edge Cases ====================
def test_timeout_scenario(client):
    """Test that the client handles a request timeout."""
    with patch.object(client.session, 'post', side_effect=requests.exceptions.Timeout):
        with pytest.raises(AbacusAPIError, match="Request to /test failed:"):
            client._post('/test', {})


def test_connection_error_scenario(client):
    """Test that the client handles a connection error."""
    with patch.object(client.session, 'post', side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(AbacusAPIError, match="Request to /test failed:"):
            client._post('/test', {})


def test_request_exception_scenario(client):
    """Test that the client handles generic request exceptions."""
    with patch.object(client.session, 'post', side_effect=requests.exceptions.RequestException("Unknown error")):
        with pytest.raises(AbacusAPIError, match="Request to /test failed:"):
            client._post('/test', {})


# ==================== Test Logger Coverage in test_connection ====================
def test_test_connection_logs_success(client):
    """Test that test_connection logs success message."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'success': True}
    
    with patch.object(client.session, 'post', return_value=mock_response):
        with patch('sologit.api.client.logger') as mock_logger:
            result = client.test_connection()
            assert result is True
            mock_logger.info.assert_called_once_with("API connection test successful")


def test_test_connection_logs_failure(client):
    """Test that test_connection logs failure message."""
    with patch.object(client.session, 'post', side_effect=AbacusAPIError("Connection failed")):
        with patch('sologit.api.client.logger') as mock_logger:
            result = client.test_connection()
            assert result is False
            mock_logger.error.assert_called_once()
            args = mock_logger.error.call_args[0]
            assert "API connection test failed:" in args[0]
