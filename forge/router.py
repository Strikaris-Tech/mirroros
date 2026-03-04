"""
Model Router - Route agent requests to appropriate LLM backends
Supports OpenRouter (Claude, GPT, etc.), Ollama, and MLX
Includes streaming support for real-time token generation
"""

import sys
from pathlib import Path

# Add project root to path to allow importing from 'agents'
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os
import json
import httpx
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from functools import lru_cache



class ModelRouter:
    """Route agent requests to LLM backends"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backends = config.get("backends", {})

    async def chat(
        self,
        agent_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send chat request to appropriate backend.

        Args:
            agent_config: Agent configuration from AgentLoader
            messages: List of message dicts with "role" and "content"
            temperature: Override agent temperature
            max_tokens: Override agent max_tokens

        Returns:
            Dict with response, model info, and metadata
        """
        backend = agent_config.get("backend", "openrouter")
        model = agent_config.get("model")
        temp = temperature if temperature is not None else agent_config.get("temperature", 0.7)
        max_tok = max_tokens if max_tokens is not None else agent_config.get("max_tokens", 2000)

        # Inject system prompt as first message if not present
        if messages and messages[0].get("role") != "system":
            system_prompt = agent_config.get("system_prompt", "")
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

        # Route to backend
        if backend == "openrouter":
            return await self._route_openrouter(model, messages, temp, max_tok)
        elif backend == "ollama":
            return await self._route_ollama(model, messages, temp, max_tok)
        elif backend == "mlx":
            return await self._route_mlx(model, messages, temp, max_tok)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    async def _route_openrouter(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """
        Route to OpenRouter API (Claude, GPT-4, etc.)

        OpenRouter provides unified access to multiple model providers.
        Docs: https://openrouter.ai/docs
        """
        openrouter_config = self.backends.get("openrouter", {})
        base_url = openrouter_config.get("base_url", "https://openrouter.ai/api/v1")
        api_key = os.getenv(openrouter_config.get("api_key_env", "OPENROUTER_API_KEY"))

        if not api_key:
            raise ValueError(
                f"OpenRouter API key not found. Set {openrouter_config.get('api_key_env')} "
                "environment variable."
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://mirroros.local",  # Optional
            "X-Title": "MirrorOS Forge",  # Optional
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract response
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        return {
            "response": content,
            "model": data.get("model", model),
            "backend": "openrouter",
            "usage": data.get("usage", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _route_ollama(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """
        Route to local Ollama instance.

        Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md
        """
        ollama_config = self.backends.get("ollama", {})
        base_url = ollama_config.get("base_url", "http://localhost:11434")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "response": data.get("message", {}).get("content", ""),
            "model": model,
            "backend": "ollama",
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _route_mlx(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """
        Route to local MLX API server (Apple Silicon optimized).
        """
        mlx_config = self.backends.get("mlx", {})
        base_url = mlx_config.get("base_url", "http://localhost:8000")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "response": data.get("response", ""),
            "model": model,
            "backend": "mlx",
            "usage": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def chat_stream(
        self,
        agent_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response token by token or as tool calls.

        Args:
            agent_config: Agent configuration from AgentLoader
            messages: List of message dicts with "role" and "content"
            temperature: Override agent temperature
            max_tokens: Override agent max_tokens

        Yields:
            Dicts representing tokens or tool calls
        """
        backend = agent_config.get("backend", "openrouter")
        model = agent_config.get("model")
        temp = temperature if temperature is not None else agent_config.get("temperature", 0.7)
        max_tok = max_tokens if max_tokens is not None else agent_config.get("max_tokens", 2000)

        # Only enable tools for agents that have tool_calling enabled
        enable_tools = agent_config.get("tool_calling", False)

        # Inject system prompt as first message if not present
        if messages and messages[0].get("role") != "system":
            system_prompt = agent_config.get("system_prompt", "")
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

        # Route to backend
        if backend == "ollama":
            async for event in self._route_ollama_stream(model, messages, temp, max_tok, enable_tools):
                yield event
        else:
            # Fall back to non-streaming for other backends, but yield a compatible format
            result = await self.chat(agent_config, messages, temperature, max_tokens)
            yield {"type": "token", "content": result["response"]}

    async def _route_ollama_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        enable_tools: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Ollama token by token.
        Optionally supports function calling if enable_tools is True.

        Yields individual tokens or tool call requests.
        """
        ollama_config = self.backends.get("ollama", {})
        base_url = ollama_config.get("base_url", "http://localhost:11434")

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,  # Enable streaming
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        # Only add tools for agents with tool_calling enabled
        if enable_tools:
            tool_schema = self._get_tool_schema()
            if tool_schema:
                payload["tools"] = tool_schema

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            
                            # Check for a tool call
                            if chunk.get("message", {}).get("tool_calls"):
                                tool_calls = chunk["message"]["tool_calls"]
                                for tool_call in tool_calls:
                                    yield {"type": "tool_call", "data": tool_call}
                                continue

                            # Otherwise, yield the content token
                            if chunk.get("message") and chunk["message"].get("content"):
                                yield {"type": "token", "content": chunk["message"]["content"]}

                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue

    def list_available_models(self) -> Dict[str, List[str]]:
        """
        List all available models across backends.

        Returns:
            Dict mapping backend name to list of available models
        """
        available = {}

        # OpenRouter models
        if "openrouter" in self.backends:
            or_models = self.backends["openrouter"].get("models", {})
            available["openrouter"] = list(or_models.values())

        # Ollama models
        if "ollama" in self.backends:
            available["ollama"] = self.backends["ollama"].get("models", [])

        # MLX models
        if "mlx" in self.backends and self.backends["mlx"].get("enabled"):
            available["mlx"] = ["local"]

        return available

    @lru_cache(maxsize=1)
    def _get_tool_schema(self) -> List[Dict[str, Any]]:
        """
        Generate the tool schema for function calling.

        Override this method in a subclass or agent adapter to expose
        custom tool definitions. Returns an empty list by default —
        add your adapter's tools here.

        Returns:
            List of tool schema dicts in OpenAI function-calling format.
        """
        return []
