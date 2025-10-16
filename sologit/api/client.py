
"""
Abacus.ai API client for Solo Git.

Provides a Python client for interacting with the Abacus.ai RouteLLM API
for all AI operations (planning, coding, fast ops).
"""

import requests
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

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
    tokens_used: int
    finish_reason: str


class AbacusClient:
    """Client for Abacus.ai RouteLLM API."""
    
    def __init__(self, config: AbacusAPIConfig):
        """
        Initialize Abacus.ai client.
        
        Args:
            config: API configuration with endpoint and key
        """
        self.endpoint = config.endpoint
        self.api_key = config.api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """
        Test the API connection with a simple request.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.chat(
                messages=[ChatMessage(role='user', content='test')],
                model='llama-3.1-8b-instruct',
                max_tokens=5
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        **kwargs
    ) -> ChatResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of chat messages
            model: Model identifier (e.g., 'gpt-4o', 'deepseek-coder-33b')
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
        
        Returns:
            ChatResponse with generated content
        
        Raises:
            Exception if API request fails
        """
        url = f"{self.endpoint}/chat/completions"
        
        payload = {
            'model': model,
            'messages': [{'role': m.role, 'content': m.content} for m in messages],
            'max_tokens': max_tokens,
            'temperature': temperature,
            **kwargs
        }
        
        logger.debug(f"Sending chat request to {model}")
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return ChatResponse(
            content=data['choices'][0]['message']['content'],
            model=data['model'],
            tokens_used=data['usage']['total_tokens'],
            finish_reason=data['choices'][0]['finish_reason']
        )
    
    def stream_chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion response.
        
        Args:
            messages: List of chat messages
            model: Model identifier
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
        
        Yields:
            Content chunks as they arrive
        """
        url = f"{self.endpoint}/chat/completions"
        
        payload = {
            'model': model,
            'messages': [{'role': m.role, 'content': m.content} for m in messages],
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': True,
            **kwargs
        }
        
        logger.debug(f"Streaming chat request to {model}")
        
        response = self.session.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        import json
                        data = json.loads(data_str)
                        content = data['choices'][0].get('delta', {}).get('content')
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

