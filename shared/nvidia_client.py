"""
AIforBharat — NVIDIA NIM Client
=================================
Unified client for NVIDIA Build API endpoints.
Supports Llama 3.1 70B/8B, embedding, reranking models.
Uses the OpenAI-compatible API format.

Includes an LLM Circuit Breaker to protect against NIM outages:
- CLOSED: Normal operation, all calls go through.
- OPEN: After N consecutive failures, reject immediately with fallback.
- HALF_OPEN: After cooldown, allow 1 probe request.
"""

import logging
import time
from typing import Any, Optional
from openai import OpenAI
from shared.config import settings

logger = logging.getLogger("nvidia_client")


# ══════════════════════════════════════════════════════════════════════════════
# LLM CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════════════════

NIM_DEGRADED_MESSAGE = (
    "Our AI knowledge service is temporarily unavailable. "
    "Please check back in a minute or browse our direct scheme list."
)


class LLMCircuitBreaker:
    """
    Circuit breaker specifically for NVIDIA NIM API calls.
    States: CLOSED → OPEN → HALF_OPEN → CLOSED.

    - CLOSED: Forward all requests.
    - OPEN: Reject immediately after `failure_threshold` consecutive failures.
    - HALF_OPEN: After `cooldown_seconds`, allow 1 probe request.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = None, cooldown_seconds: int = None):
        self._failure_threshold = failure_threshold or settings.LLM_CB_FAILURE_THRESHOLD
        self._cooldown_seconds = cooldown_seconds or settings.LLM_CB_COOLDOWN_SECONDS
        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = 0.0
        self._total_trips = 0  # how many times we've opened

    @property
    def state(self) -> str:
        """Get current state, auto-transitioning OPEN → HALF_OPEN after cooldown."""
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time > self._cooldown_seconds:
                self._state = self.HALF_OPEN
                logger.info("LLM Circuit Breaker → HALF_OPEN (cooldown expired, allowing probe)")
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == self.OPEN

    def allow_request(self) -> bool:
        s = self.state
        return s in (self.CLOSED, self.HALF_OPEN)

    def record_success(self):
        if self._state in (self.HALF_OPEN, self.OPEN):
            logger.info("LLM Circuit Breaker → CLOSED (probe succeeded)")
        self._consecutive_failures = 0
        self._state = self.CLOSED

    def record_failure(self):
        self._consecutive_failures += 1
        self._last_failure_time = time.time()
        if self._consecutive_failures >= self._failure_threshold:
            if self._state != self.OPEN:
                self._total_trips += 1
                logger.warning(
                    f"LLM Circuit Breaker → OPEN after {self._consecutive_failures} "
                    f"consecutive failures (trip #{self._total_trips}). "
                    f"Cooldown: {self._cooldown_seconds}s"
                )
            self._state = self.OPEN

    def get_status(self) -> dict:
        return {
            "state": self.state,
            "consecutive_failures": self._consecutive_failures,
            "total_trips": self._total_trips,
            "cooldown_seconds": self._cooldown_seconds,
            "failure_threshold": self._failure_threshold,
        }


# Singleton circuit breaker for NIM
llm_circuit_breaker = LLMCircuitBreaker()


class NVIDIAClient:
    """
    Client for NVIDIA NIM API endpoints.
    Uses OpenAI-compatible SDK since NIM exposes the same interface.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.NVIDIA_API_KEY
        self.base_url = base_url or settings.NVIDIA_BASE_URL
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        logger.info(f"NVIDIA NIM client initialized: {self.base_url}")

    def chat_completion(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> Any:
        """
        Send a chat completion request to NVIDIA NIM.
        Protected by LLM circuit breaker — returns degraded fallback
        when NIM is unreachable.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID (defaults to Llama 3.1 8B).
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
        
        Returns:
            OpenAI ChatCompletion response object.
        
        Raises:
            NIMUnavailableError: When circuit breaker is OPEN.
        """
        model = model or settings.NIM_MODEL_8B

        # ── Circuit breaker guard ─────────────────────────────────────
        if not llm_circuit_breaker.allow_request():
            logger.warning(f"LLM Circuit Breaker OPEN — returning degraded fallback for chat_completion")
            raise NIMUnavailableError(NIM_DEGRADED_MESSAGE)

        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=stream,
            )

            if stream:
                llm_circuit_breaker.record_success()
                return completion  # Returns an iterator

            llm_circuit_breaker.record_success()
            logger.info(
                f"NIM completion: model={model}, "
                f"tokens={completion.usage.total_tokens if completion.usage else 'N/A'}"
            )
            return completion

        except NIMUnavailableError:
            raise
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"NVIDIA NIM API error: {e}")
            raise

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant for Indian government schemes.",
        model: str = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """
        Simple text generation helper. Protected by circuit breaker.
        
        Args:
            prompt: User prompt.
            system_prompt: System instruction.
            model: Model to use.
            max_tokens: Maximum output tokens.
            temperature: Sampling temperature.
        
        Returns:
            Generated text string.
        
        Raises:
            NIMUnavailableError: When circuit breaker is OPEN.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = self.chat_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def generate_embedding(self, text: str, model: str = None) -> list[float]:
        """
        Generate an embedding vector for the given text. Protected by circuit breaker.
        """
        model = model or settings.EMBEDDING_MODEL

        if not llm_circuit_breaker.allow_request():
            logger.warning("LLM Circuit Breaker OPEN — returning degraded fallback for embedding")
            raise NIMUnavailableError(NIM_DEGRADED_MESSAGE)

        try:
            response = self.client.embeddings.create(
                model=model,
                input=text,
            )
            llm_circuit_breaker.record_success()
            return response.data[0].embedding
        except NIMUnavailableError:
            raise
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"Embedding API error: {e}")
            raise

    def generate_embeddings_batch(self, texts: list[str], model: str = None) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts. Protected by circuit breaker.
        """
        model = model or settings.EMBEDDING_MODEL

        if not llm_circuit_breaker.allow_request():
            logger.warning("LLM Circuit Breaker OPEN — returning degraded fallback for batch embedding")
            raise NIMUnavailableError(NIM_DEGRADED_MESSAGE)

        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts,
            )
            llm_circuit_breaker.record_success()
            return [item.embedding for item in response.data]
        except NIMUnavailableError:
            raise
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"Batch embedding API error: {e}")
            raise


class NIMUnavailableError(Exception):
    """Raised when the LLM circuit breaker is OPEN and NIM calls are blocked."""
    pass


# ── Singleton client ──────────────────────────────────────────────────────────
nvidia_client = NVIDIAClient()


def get_nvidia_client() -> NVIDIAClient:
    """Get the singleton NVIDIA NIM client."""
    return nvidia_client


def get_llm_circuit_breaker_status() -> dict:
    """Get the current LLM circuit breaker status (for monitoring endpoints)."""
    return llm_circuit_breaker.get_status()
