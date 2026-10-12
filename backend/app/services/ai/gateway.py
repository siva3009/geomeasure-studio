"""
AI Provider Gateway for GeoMeasure Studio.
Manages provider routing, fallback policies, connection pooling, and privacy constraints.
"""

import logging
import time
from typing import Dict, Any, List, Optional
import httpx

from app.config import settings
from app.services.ai.providers import (
    BaseAIProvider,
    OllamaProvider,
    GroqHostedProvider,
    GenericOpenAIProvider,
    MockAIProvider,
    ProviderResult,
    ProviderError,
)

logger = logging.getLogger(__name__)


class AIGateway:
    """Gateway orchestrating AI requests across local Ollama and hosted providers."""

    def __init__(self):
        # Persistent shared HTTP client for connection reuse and lower latency
        self._http_client = httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds)
        self._mock_provider: Optional[BaseAIProvider] = None

        # Standard providers
        self._ollama = OllamaProvider(client=self._http_client)
        self._groq = GroqHostedProvider(client=self._http_client)
        self._fallback: Optional[GenericOpenAIProvider] = None
        if settings.ai_fallback_base_url and settings.ai_fallback_api_key:
            self._fallback = GenericOpenAIProvider(client=self._http_client)

    def set_mock_provider(self, mock: Optional[BaseAIProvider]):
        """Inject or remove a mock provider for automated deterministic testing."""
        self._mock_provider = mock

    async def aclose(self):
        """Close shared HTTP client."""
        if not self._http_client.is_closed:
            await self._http_client.aclose()

    def is_local_safe(self) -> bool:
        """Verify whether local Ollama endpoint is valid for the current environment."""
        base_url = settings.ollama_base_url.lower()
        is_loopback = any(h in base_url for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
        if settings.environment == "production" and is_loopback:
            # Render or public cloud cannot connect to a visitor's localhost
            return False
        return True

    def resolve_provider_sequence(
        self,
        mode_override: Optional[str] = None,
        privacy_override: Optional[str] = None
    ) -> List[str]:
        """Determine the prioritized order of provider candidates."""
        privacy = privacy_override or settings.ai_privacy_mode
        mode = mode_override or settings.effective_ai_provider_mode

        if privacy == "local_only":
            return ["local"]

        if mode == "local_only":
            return ["local"]
        elif mode == "hosted_only":
            return ["hosted", "fallback"]
        elif mode == "hosted_first":
            return ["hosted", "local", "fallback"] if self.is_local_safe() else ["hosted", "fallback"]
        else:
            # local_first default
            if not self.is_local_safe():
                logger.info("Local Ollama endpoint is loopback in production environment. Routing to hosted.")
                return ["hosted", "fallback"]
            return ["local", "hosted", "fallback"]

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        mode_override: Optional[str] = None,
        privacy_override: Optional[str] = None,
        timeout_seconds: Optional[float] = None
    ) -> ProviderResult:
        """
        Execute completion with strict privacy mode enforcement and automatic failover.
        """
        if self._mock_provider is not None:
            return await self._mock_provider.complete(messages, tools, timeout_seconds)

        sequence = self.resolve_provider_sequence(mode_override, privacy_override)
        errors: List[str] = []

        for provider_key in sequence:
            try:
                if provider_key == "local":
                    if not self.is_local_safe():
                        errors.append("Local Ollama cannot be called from hosted cloud environment.")
                        continue
                    # Tight local budget when fallback is available
                    local_timeout = min(timeout_seconds or settings.ai_request_timeout_seconds, 6.0) if len(sequence) > 1 else (timeout_seconds or settings.ai_request_timeout_seconds)
                    return await self._ollama.complete(messages, tools, timeout_seconds=local_timeout)

                elif provider_key == "hosted":
                    if not settings.groq_api_key:
                        errors.append("Groq hosted provider is not configured (missing GROQ_API_KEY).")
                        continue
                    return await self._groq.complete(messages, tools, timeout_seconds=timeout_seconds)

                elif provider_key == "fallback":
                    if self._fallback and settings.ai_fallback_api_key:
                        return await self._fallback.complete(messages, tools, timeout_seconds=timeout_seconds)
                    errors.append("Fallback provider not configured.")

            except ProviderError as pe:
                logger.warning("Provider %s failed: %s (timeout=%s, rate_limit=%s)", provider_key, str(pe), pe.is_timeout, pe.is_rate_limit)
                errors.append(f"{provider_key}: {str(pe)}")
                # If privacy mode prohibits cloud transmission, DO NOT attempt hosted fallback
                privacy = privacy_override or settings.ai_privacy_mode
                if privacy == "local_only" and provider_key == "local":
                    raise ProviderError(
                        f"Local inference failed and cloud fallback is prohibited under local_only privacy mode: {str(pe)}",
                        provider="local"
                    )
            except Exception as ex:
                logger.error("Unexpected error in provider %s: %s", provider_key, str(ex))
                errors.append(f"{provider_key}: {str(ex)}")

        # If all candidates failed
        combined = " | ".join(errors) if errors else "No AI providers available"
        raise ProviderError(f"All eligible AI providers failed: {combined}", provider="gateway")

    async def get_health_status(self) -> Dict[str, Any]:
        """Check availability and readiness of configured providers."""
        if self._mock_provider:
            return {
                "active_mode": "mock",
                "mock": await self._mock_provider.check_health(),
            }

        local_health = await self._ollama.check_health() if self.is_local_safe() else {"status": "disabled_in_cloud"}
        groq_health = await self._groq.check_health() if settings.groq_api_key else {"status": "unconfigured"}

        return {
            "effective_mode": settings.effective_ai_provider_mode,
            "privacy_mode": settings.ai_privacy_mode,
            "local_ollama": local_health,
            "hosted_groq": groq_health,
            "fallback_configured": bool(settings.ai_fallback_api_key and settings.ai_fallback_base_url),
        }


# Global gateway singleton
ai_gateway = AIGateway()
