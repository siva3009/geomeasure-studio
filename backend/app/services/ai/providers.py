"""
Modular AI Provider Adapters for GeoMeasure Studio.
Supports Local Ollama (qwen3.5:2b), Hosted Groq, Generic OpenAI-compatible endpoints,
and Mock provider for fast deterministic testing.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when an AI provider fails or encounters a timeout."""
    def __init__(self, message: str, provider: str, is_timeout: bool = False, is_rate_limit: bool = False):
        super().__init__(message)
        self.provider = provider
        self.is_timeout = is_timeout
        self.is_rate_limit = is_rate_limit


class ProviderResult:
    """Standardized output from any AI provider."""
    def __init__(
        self,
        content: str,
        provider: str,
        model: str,
        is_local: bool,
        latency_ms: float,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.is_local = is_local
        self.latency_ms = latency_ms
        self.tool_calls = tool_calls or []
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class BaseAIProvider(ABC):
    """Abstract interface for AI inference providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        pass

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: Optional[float] = None
    ) -> ProviderResult:
        """Execute chat completion with optional tool definitions."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform a quick health/reachability check."""
        pass


class OllamaProvider(BaseAIProvider):
    """Local inference provider via Ollama."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self._client = client

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_local(self) -> bool:
        return True

    def _get_client(self, timeout: float) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(timeout=timeout)

    async def check_health(self) -> Dict[str, Any]:
        timeout = 2.0
        try:
            client = self._get_client(timeout)
            should_close = self._client is None
            try:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    model_found = any(self.model in m for m in models)
                    return {
                        "status": "healthy" if model_found else "model_missing",
                        "available_models": models,
                        "target_model": self.model,
                        "model_ready": model_found,
                    }
                return {"status": "unhealthy", "error": f"HTTP {res.status_code}"}
            finally:
                if should_close:
                    await client.aclose()
        except Exception as e:
            return {"status": "offline", "error": str(e), "target_model": self.model}

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: Optional[float] = None
    ) -> ProviderResult:
        timeout = timeout_seconds or settings.ai_request_timeout_seconds
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": settings.ai_max_output_tokens,
            }
        }
        if tools:
            payload["tools"] = tools

        start_time = time.perf_counter()
        client = self._get_client(timeout)
        should_close = self._client is None

        try:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if res.status_code == 404:
                raise ProviderError(
                    f"Model '{self.model}' not found in local Ollama. Run: ollama run {self.model}",
                    provider="ollama"
                )
            if res.status_code != 200:
                raise ProviderError(
                    f"Ollama chat error (HTTP {res.status_code}): {res.text}",
                    provider="ollama"
                )

            data = res.json()
            message = data.get("message") or {}
            content = message.get("content") or ""

            # Extract tool calls if returned
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    fn = tc.get("function") or {}
                    tool_calls.append({
                        "name": fn.get("name"),
                        "arguments": fn.get("arguments") or {}
                    })

            p_tokens = data.get("prompt_eval_count")
            c_tokens = data.get("eval_count")
            t_tokens = (p_tokens + c_tokens) if (p_tokens is not None and c_tokens is not None) else None

            return ProviderResult(
                content=content,
                provider="ollama",
                model=self.model,
                is_local=True,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
            )
        except httpx.TimeoutException as e:
            raise ProviderError(f"Ollama request timed out after {timeout}s", provider="ollama", is_timeout=True) from e
        except httpx.ConnectError as e:
            raise ProviderError(f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running.", provider="ollama") from e
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"Ollama unexpected error: {str(e)}", provider="ollama") from e
        finally:
            if should_close:
                await client.aclose()


class GroqHostedProvider(BaseAIProvider):
    """Hosted low-latency provider using Groq's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")
        self._client = client

    @property
    def name(self) -> str:
        return "groq"

    @property
    def is_local(self) -> bool:
        return False

    def _get_client(self, timeout: float) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(timeout=timeout)

    async def check_health(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "unconfigured", "error": "GROQ_API_KEY is not set"}
        timeout = 3.0
        client = self._get_client(timeout)
        should_close = self._client is None
        try:
            res = await client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return {"status": "healthy" if res.status_code == 200 else f"HTTP {res.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}
        finally:
            if should_close:
                await client.aclose()

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: Optional[float] = None
    ) -> ProviderResult:
        if not self.api_key:
            raise ProviderError("Groq API key not configured.", provider="groq")

        timeout = timeout_seconds or settings.ai_request_timeout_seconds
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": settings.ai_max_output_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        client = self._get_client(timeout)
        should_close = self._client is None

        try:
            res = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if res.status_code == 429:
                raise ProviderError("Groq rate limit exceeded.", provider="groq", is_rate_limit=True)
            if res.status_code != 200:
                raise ProviderError(f"Groq API error (HTTP {res.status_code}): {res.text}", provider="groq")

            data = res.json()
            choices = data.get("choices") or []
            if not choices:
                raise ProviderError("Groq returned empty choices.", provider="groq")

            message = choices[0].get("message") or {}
            content = message.get("content") or ""

            # Extract tool calls
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    fn = tc.get("function") or {}
                    args_raw = fn.get("arguments") or "{}"
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    tool_calls.append({
                        "name": fn.get("name"),
                        "arguments": args
                    })

            usage = data.get("usage") or {}
            p_tokens = usage.get("prompt_tokens")
            c_tokens = usage.get("completion_tokens")
            t_tokens = usage.get("total_tokens")

            return ProviderResult(
                content=content,
                provider="groq",
                model=self.model,
                is_local=False,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
            )
        except httpx.TimeoutException as e:
            raise ProviderError(f"Groq request timed out after {timeout}s", provider="groq", is_timeout=True) from e
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"Groq unexpected error: {str(e)}", provider="groq") from e
        finally:
            if should_close:
                await client.aclose()


class GenericOpenAIProvider(GroqHostedProvider):
    """Generic OpenAI-compatible inference provider for optional fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(
            api_key=api_key or settings.ai_fallback_api_key,
            model=model or settings.ai_fallback_model or "gpt-4o-mini",
            base_url=base_url or settings.ai_fallback_base_url or "https://api.openai.com/v1",
            client=client,
        )

    @property
    def name(self) -> str:
        return "openai_compatible"


class MockAIProvider(BaseAIProvider):
    """Deterministic mock provider for automated tests and CI environments."""

    def __init__(
        self,
        name: str = "mock_provider",
        is_local: bool = True,
        responses: Optional[List[ProviderResult]] = None,
        should_fail: bool = False,
        error_message: str = "Simulated provider failure",
        is_timeout: bool = False,
    ):
        self._name = name
        self._is_local = is_local
        self._responses = responses or []
        self._should_fail = should_fail
        self._error_message = error_message
        self._is_timeout = is_timeout
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_local(self) -> bool:
        return self._is_local

    async def check_health(self) -> Dict[str, Any]:
        return {"status": "healthy" if not self._should_fail else "unhealthy"}

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: Optional[float] = None
    ) -> ProviderResult:
        self.call_count += 1
        if self._should_fail:
            raise ProviderError(self._error_message, provider=self._name, is_timeout=self._is_timeout)

        if self._responses:
            return self._responses.pop(0)

        # Default synthetic response with tool selection based on keywords in user message
        user_msg = messages[-1].get("content", "").lower() if messages else ""
        tool_calls = []

        if "rank" in user_msg or "largest" in user_msg:
            tool_calls.append({"name": "measure_features", "arguments": {"rank_by": "area", "limit": 5}})
        elif "validate" in user_msg or "overlap" in user_msg:
            tool_calls.append({"name": "validate_geometries", "arguments": {"check_overlaps": True}})
        elif "export" in user_msg:
            fmt = "geojson" if "geojson" in user_msg else "csv"
            tool_calls.append({"name": "export_results", "arguments": {"format": fmt}})
        else:
            tool_calls.append({"name": "inspect_dataset", "arguments": {"include_attributes": True}})

        return ProviderResult(
            content="I have analyzed your dataset using the approved GIS tools.",
            provider=self._name,
            model="mock-qwen-2b",
            is_local=self._is_local,
            latency_ms=12.5,
            tool_calls=tool_calls,
            prompt_tokens=45,
            completion_tokens=25,
            total_tokens=70,
        )
