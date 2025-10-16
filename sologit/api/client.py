
"""
Abacus.ai API client for Solo Git.

Provides a Python client for interacting with the Abacus.ai API
for all AI operations (planning, coding, fast ops).

Note: Abacus.ai uses a deployment-based API model. For chatbot operations,
you need:
1. A deployment ID (from your Abacus.ai chatbot/agent)
2. A deployment token (generated for that deployment)
3. The service API key (s2_... format)

For OpenAI-compatible RouteLLM access, you need a ChatLLM subscription.
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
    """
    Client for Abacus.ai API.
    
    This client uses the Abacus.ai native API format with deployment-based
    chatbot interactions. To use this client, you need:
    
    1. Service API Key (s2_...) - configured in config.yaml
    2. Deployment ID - from your Abacus.ai chatbot/agent  
    3. Deployment Token - generated for your deployment
    
    For Phase 0, we provide a simple connection test. Full chatbot
    integration will be completed in Phase 2 with proper deployment
    configuration.
    """
    
    def __init__(self, config: AbacusAPIConfig):
        """
        Initialize Abacus.ai client.
        
        Args:
            config: API configuration with endpoint and key
        """
        # Abacus.ai API uses /api/v0/ endpoints, not /v1/
        if '/v1' in config.endpoint:
            self.endpoint = config.endpoint.replace('/v1', '/api/v0')
            logger.debug(f"Adjusted endpoint to Abacus.ai format: {self.endpoint}")
        elif not config.endpoint.endswith('/api/v0'):
            # Ensure proper endpoint format
            base = config.endpoint.rstrip('/')
            self.endpoint = f"{base}/api/v0"
        else:
            self.endpoint = config.endpoint
            
        self.api_key = config.api_key
        self.session = requests.Session()
        # Abacus.ai uses 'apiKey' header, not 'Authorization: Bearer'
        self.session.headers.update({
            'apiKey': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """
        Test the API connection with a simple request.
        
        Tests the API key by attempting to list API keys (which validates auth).
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Use a simple endpoint that just validates authentication
            # The listApiKeys endpoint will return a list (possibly empty) if auth is valid
            url = f"{self.endpoint}/listApiKeys"
            response = self.session.post(url, json={})
            
            if response.status_code == 200:
                data = response.json()
                # If we get a success response, authentication is valid
                if data.get('success', True):  # Some endpoints don't include 'success' field
                    logger.info("API connection test successful")
                    return True
                else:
                    logger.error(f"API returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error(f"API connection test failed: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Send a chat completion request to an Abacus.ai deployment.
        
        Note: This method requires a deployed chatbot/agent on Abacus.ai.
        Full implementation will be completed in Phase 2.
        
        Args:
            messages: List of chat messages
            model: Model identifier (for logging/reference)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            deployment_id: Abacus.ai deployment ID (required)
            deployment_token: Deployment authentication token (required)
            **kwargs: Additional parameters
        
        Returns:
            ChatResponse with generated content
        
        Raises:
            ValueError: If deployment credentials are missing
            Exception: If API request fails
        """
        if not deployment_id or not deployment_token:
            raise ValueError(
                "Abacus.ai requires deployment_id and deployment_token. "
                "To use this API:\n"
                "1. Create a chatbot/agent at https://abacus.ai\n"
                "2. Get the deployment ID from the deployment page\n"
                "3. Generate a deployment token\n"
                "4. Pass both to this method\n\n"
                "Full deployment integration will be added in Phase 2."
            )
        
        url = f"{self.endpoint}/getChatResponse"
        
        # Convert messages to Abacus.ai format (uses 'text' instead of 'content')
        abacus_messages = [
            {'role': m.role, 'text': m.content} 
            for m in messages
        ]
        
        payload = {
            'deploymentId': deployment_id,
            'deploymentToken': deployment_token,
            'messages': abacus_messages,
            **kwargs
        }
        
        logger.debug(f"Sending chat request to deployment {deployment_id}")
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse Abacus.ai response format
        # Note: Actual response format may vary - this is a placeholder
        if not data.get('success', False):
            raise Exception(f"API error: {data.get('error', 'Unknown error')}")
        
        # Extract response content (format TBD based on actual API response)
        content = data.get('response', data.get('content', ''))
        
        return ChatResponse(
            content=content,
            model=model,  # Abacus.ai may not return model name
            tokens_used=data.get('tokensUsed', 0),
            finish_reason='stop'
        )
    
    def stream_chat(
        self,
        messages: List[ChatMessage],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        deployment_id: Optional[str] = None,
        deployment_token: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream a chat completion response from an Abacus.ai deployment.
        
        Note: This method requires a deployed chatbot/agent on Abacus.ai.
        Full implementation will be completed in Phase 2.
        
        Args:
            messages: List of chat messages
            model: Model identifier (for logging/reference)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            deployment_id: Abacus.ai deployment ID (required)
            deployment_token: Deployment authentication token (required)
            **kwargs: Additional parameters
        
        Yields:
            Content chunks as they arrive
        """
        if not deployment_id or not deployment_token:
            raise ValueError(
                "Abacus.ai requires deployment_id and deployment_token for streaming. "
                "Full deployment integration will be added in Phase 2."
            )
        
        url = f"{self.endpoint}/getStreamingChatResponse"
        
        # Convert messages to Abacus.ai format
        abacus_messages = [
            {'role': m.role, 'text': m.content} 
            for m in messages
        ]
        
        payload = {
            'deploymentId': deployment_id,
            'deploymentToken': deployment_token,
            'messages': abacus_messages,
            **kwargs
        }
        
        logger.debug(f"Streaming chat request to deployment {deployment_id}")
        
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
                        # Extract content from Abacus.ai streaming format
                        content = data.get('content', data.get('text', ''))
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

