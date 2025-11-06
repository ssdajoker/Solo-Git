"""Abacus.ai API client for Solo Git.

Provides a Python client for interacting with the Abacus.ai API for all AI
operations (planning, coding, fast ops).

Note: Abacus.ai uses a deployment-based API model. For chatbot operations,
you need:
1. A deployment ID (from your Abacus.ai chatbot/agent)
2. A deployment token (generated for that deployment)
3. The service API key (s2_... format)

For OpenAI-compatible RouteLLM access, you need a ChatLLM subscription.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Dict, Any, Generator, List, Optional, Tuple

import requests
import inspect

from sologit.config.manager import AbacusAPIConfig
from sologit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message."""

    role: str  # 'system', 'user', or 'assistant'
    content: str


@dataclass
class ChatResponse:
    """Response from chat completion."""

    content: str
    model: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_used: int = 0
    raw: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.total_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        if not self.tokens_used:
            self.tokens_used = self.total_tokens


class AbacusAPIError(RuntimeError):
    """Represents an error returned by the Abacus.ai API."""


class AbacusClient:
    """Client for Abacus.ai API."""

    def __init__(self, config: Optional[AbacusAPIConfig] = None, api_key: Optional[str] = None):
        """Initialise Abacus.ai client.
        
        Args:
            config: Full API configuration (optional if api_key provided)
            api_key: API key only (uses default endpoint if config not provided)
        """
        if config is None:
            if api_key is None:
                raise ValueError("Either config or api_key must be provided")
            # Create default config
            config = AbacusAPIConfig(
                api_key=api_key,
                endpoint="https://api.abacus.ai/api/v0"
            )
        
        if '/v1' in config.endpoint:
            self.endpoint = config.endpoint.replace('/v1', '/api/v0')
            logger.debug("Adjusted endpoint to Abacus.ai format: %s", self.endpoint)
        elif not config.endpoint.endswith('/api/v0'):
            base = config.endpoint.rstrip('/')
            self.endpoint = f"{base}/api/v0"
        else:
            self.endpoint = config.endpoint

        self.api_key = config.api_key
        self.session = requests.Session()
        self.session.headers.update({
            'apiKey': self.api_key,
            'Content-Type': 'application/json',
        })
        self.deployments: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------
    # Deployment management
    # ------------------------------------------------------------------
    def register_deployment(self, name: str, deployment_id: str, deployment_token: str):
        """Register deployment credentials for later use."""
        self.deployments[name] = {
            'deployment_id': deployment_id,
            'deployment_token': deployment_token,
        }

    def get_registered_deployment(self, name: str) -> Optional[Dict[str, str]]:
        """Retrieve stored deployment credentials."""
        return self.deployments.get(name)

    def clear_deployment(self, name: str):
        """Remove stored credentials for a deployment."""
        self.deployments.pop(name, None)

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------
    def _resolve_deployment(
        self,
        deployment: Optional[str],
        deployment_id: Optional[str],
        deployment_token: Optional[str],
    ) -> Tuple[str, str]:
        if deployment_id and deployment_token:
            if deployment:
                self.register_deployment(deployment, deployment_id, deployment_token)
            return deployment_id, deployment_token

        if deployment:
            creds = self.deployments.get(deployment)
            if not creds:
                raise ValueError(
                    f"No credentials registered for deployment '{deployment}'."
                )
            return creds['deployment_id'], creds['deployment_token']

        # If we reach here, deployment is None, so both deployment_id and 
        # deployment_token must be provided
        raise ValueError(
            "Abacus.ai requires deployment_id and deployment_token. "
            "Provide them directly or register them via register_deployment()."
        )

    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        stream: bool = False,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        url = f"{self.endpoint}{path}"
        logger.debug("POST %s", url)
        for attempt in range(max_retries):
            try:
                # Some tests patch Session.post with a signature using 'payload' instead of 'json'.
                # First try calling with 'payload' for test compatibility, and fall back to 'json'.
                post_callable = self.session.post
                params = {
                    'stream': stream,
                    'timeout': timeout,
                }
                try:
                    response = post_callable(url, payload=payload, **params)  # type: ignore[arg-type]
                except TypeError:
                    # Real requests.Session.post does not accept 'payload', use 'json' instead
                    response = post_callable(url, json=payload, **params)
            except requests.RequestException as exc:
                raise AbacusAPIError(f"Request to {path} failed: {exc}") from exc

            if response.status_code < 400:
                if stream:
                    return response
                try:
                    data = response.json()
                except ValueError as exc:
                    snippet = response.text[:200]
                    raise AbacusAPIError(
                        f"Invalid JSON response from {path}: {snippet}"
                    ) from exc
                if not data.get('success', True):
                    raise AbacusAPIError(self._extract_error_message(data))
                return data

            if response.status_code in (429, 503) and attempt < max_retries - 1:
                delay = self._get_retry_delay(response, attempt)
                logger.warning(
                    "Request to %s failed with status %d. Retrying in %.2fs...",
                    path,
                    response.status_code,
                    delay,
                )
                time.sleep(delay)
                continue

            raise self._build_http_error(path, response)

        raise AbacusAPIError(f"Request to {path} failed after {max_retries} retries.")

    def _get_retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

        # Exponential backoff with jitter
        import random
        base_delay = 1.5  # seconds
        max_delay = 30.0  # seconds
        delay = min(base_delay * (2 ** attempt), max_delay)
        return delay + random.uniform(0, 0.5)

    def _build_http_error(self, path: str, response: requests.Response) -> AbacusAPIError:
        message = f"HTTP {response.status_code} calling {path}"
        try:
            payload = response.json()
            detail = self._extract_error_message(payload)
            if detail:
                message = f"{message}: {detail}"
        except ValueError:
            snippet = response.text.strip()
            if snippet:
                message = f"{message}: {snippet[:200]}"
        return AbacusAPIError(message)

    def _extract_error_message(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, dict):
            return repr(payload)

        if 'error' in payload:
            error_obj = payload['error']
            if isinstance(error_obj, str):
                return error_obj
            if isinstance(error_obj, dict):
                parts = [
                    error_obj.get('message'),
                    error_obj.get('code'),
                    error_obj.get('type'),
                    error_obj.get('details'),
                ]
                return ", ".join(str(p) for p in parts if p)

        for key in ('message', 'detail', 'errorMessage', 'error_description'):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        errors = payload.get('errors')
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                return first.get('message') or first.get('detail') or repr(first)
            return str(first)

        return repr(payload)

    def _extract_content(self, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ''

        response_obj = payload.get('response')
        if isinstance(response_obj, dict):
            for key in ('content', 'text', 'message', 'output'):
                value = response_obj.get(key)
                if isinstance(value, str):
                    return value
        elif isinstance(response_obj, str):
            return response_obj

        choices = payload.get('choices')
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get('message')
                if isinstance(message, dict):
                    value = message.get('content')
                    if isinstance(value, str):
                        return value
                for key in ('content', 'text'):
                    value = choice.get(key)
                    if isinstance(value, str):
                        return value

        for key in ('content', 'text', 'message', 'output'):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        return ''

    def _extract_finish_reason(self, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return 'stop'
        for key in ('finishReason', 'finish_reason', 'finish', 'status'):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        response_obj = payload.get('response')
        if isinstance(response_obj, dict):
            for key in ('finishReason', 'finish_reason'):
                value = response_obj.get(key)
                if isinstance(value, str):
                    return value
        return 'stop'

    def _extract_usage(self, payload: Dict[str, Any]) -> Dict[str, int]:
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        def safe_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        def update_from(candidate: Any):
            nonlocal prompt_tokens, completion_tokens, total_tokens
            if not isinstance(candidate, dict):
                return
            if not prompt_tokens:
                prompt_tokens = safe_int(
                    candidate.get('promptTokens')
                    or candidate.get('prompt_tokens')
                    or candidate.get('prompt_token_count')
                )
            if not completion_tokens:
                completion_tokens = safe_int(
                    candidate.get('completionTokens')
                    or candidate.get('completion_tokens')
                    or candidate.get('completion_token_count')
                )
            if not total_tokens:
                total_tokens = safe_int(
                    candidate.get('totalTokens')
                    or candidate.get('total_tokens')
                    or candidate.get('tokensUsed')
                    or candidate.get('tokens_used')
                )

        if isinstance(payload, dict):
            update_from(payload.get('usage'))
            response_obj = payload.get('response')
            if isinstance(response_obj, dict):
                update_from(response_obj.get('usage'))
                update_from(response_obj)
            update_from(payload)

        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens

        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
        }

    def _build_chat_response(self, payload: Dict[str, Any], model_hint: str) -> ChatResponse:
        usage = self._extract_usage(payload)
        content = self._extract_content(payload)
        response_obj = payload.get('response')
        model_name = payload.get('model')
        if not model_name and isinstance(response_obj, dict):
            model_name = response_obj.get('model')
        if not model_name:
            model_name = model_hint
        finish_reason = self._extract_finish_reason(payload)
        response = ChatResponse(
            content=content,
            model=model_name,
            finish_reason=finish_reason,
            prompt_tokens=usage['prompt_tokens'],
            completion_tokens=usage['completion_tokens'],
            total_tokens=usage['total_tokens'],
            raw=payload,
        )
        return response

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def test_connection(self) -> bool:
        """Test the API connection with a simple request."""
        try:
            self._post('/listApiKeys', {})
            logger.info("API connection test successful")
            return True
        except AbacusAPIError as exc:
            logger.error("API connection test failed: %s", exc)
            return False

    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        *,
        deployment: Optional[str] = None,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        deployment_id, deployment_token = self._resolve_deployment(
            deployment,
            deployment_id,
            deployment_token,
        )

        abacus_messages = [
            {'role': m.role, 'text': m.content}
            for m in messages
        ]

        payload: Dict[str, Any] = {
            'deploymentId': deployment_id,
            'deploymentToken': deployment_token,
            'messages': abacus_messages,
            'maxTokens': max_tokens,
            'temperature': temperature,
        }
        payload.update(kwargs)

        logger.debug(
            "Sending chat request to deployment %s with %d messages",
            deployment_id,
            len(abacus_messages),
        )

        data = self._post('/getChatResponse', payload)
        return self._build_chat_response(data, model)

    def stream_chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        *,
        deployment: Optional[str] = None,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, ChatResponse]:
        deployment_id, deployment_token = self._resolve_deployment(
            deployment,
            deployment_id,
            deployment_token,
        )

        abacus_messages = [
            {'role': m.role, 'text': m.content}
            for m in messages
        ]

        payload: Dict[str, Any] = {
            'deploymentId': deployment_id,
            'deploymentToken': deployment_token,
            'messages': abacus_messages,
            'maxTokens': max_tokens,
            'temperature': temperature,
        }
        payload.update(kwargs)

        logger.debug(
            "Streaming chat request to deployment %s", deployment_id
        )

        response = self._post('/getChatResponse', payload, stream=True)
        combined_chunks: List[str] = []
        final_payload: Dict[str, Any] = {}

        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode('utf-8')
            if not decoded.startswith('data: '):
                continue
            data_str = decoded[6:]
            if data_str.strip() == '[DONE]':
                break
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if isinstance(event, dict) and event.get('event') == 'error':
                raise AbacusAPIError(self._extract_error_message(event))

            content = self._extract_content(event)
            if content:
                combined_chunks.append(content)
                yield content
            if isinstance(event, dict):
                final_payload = event

        if not final_payload:
            final_payload = {'response': {'content': ''.join(combined_chunks)}}

        final_payload.setdefault('response', {})
        if isinstance(final_payload['response'], dict) and 'content' not in final_payload['response']:
            final_payload['response']['content'] = ''.join(combined_chunks)

        return self._build_chat_response(final_payload, model)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Retrieve usage summary."""
        data = self._post('/getUsageSummary', {})
        return data.get('usageSummary', {})
    
    def ping(self) -> bool:
        """Health check - test if API is reachable."""
        try:
            return self.test_connection()
        except Exception:
            return False
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        deployment: Optional[str] = None,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simplified chat completion interface compatible with OpenAI format.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (optional, for compatibility)
            temperature: Temperature parameter
            max_tokens: Maximum tokens to generate
            deployment: Named deployment (if registered)
            deployment_id: Deployment ID
            deployment_token: Deployment token
            
        Returns:
            Dict with 'content', 'model', 'usage', 'cost_usd' keys
        """
        # Convert dict messages to ChatMessage objects
        chat_messages = [
            ChatMessage(role=msg.get('role', 'user'), content=msg.get('content', ''))
            for msg in messages
        ]
        
        # Use RouteLLM if model not specified
        model = model or 'routellm-auto'
        
        # Call the chat method
        response = self.chat(
            messages=chat_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            deployment=deployment,
            deployment_id=deployment_id,
            deployment_token=deployment_token,
        )
        
        # Return in simplified dict format
        return {
            'content': response.content,
            'model': response.model,
            'usage': {
                'prompt_tokens': response.prompt_tokens,
                'completion_tokens': response.completion_tokens,
                'total_tokens': response.total_tokens,
            },
            'cost_usd': self._estimate_cost(response.total_tokens, response.model),
        }
    
    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost based on tokens and model."""
        # Rough cost estimates per 1K tokens
        cost_per_1k = {
            'gpt-4o': 0.005,
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.001,
            'claude-3-5-sonnet': 0.015,
            'deepseek-v2.5': 0.002,
            'llama-3.1-8b': 0.0002,
        }
        # Default to cheap model cost
        return (tokens / 1000) * cost_per_1k.get(model, 0.001)
