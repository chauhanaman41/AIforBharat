"""
AIforBharat — NVIDIA NIM Client
=================================
Unified client for NVIDIA Build API endpoints.
Supports Llama 3.1 70B/8B, embedding, reranking models.
Uses the OpenAI-compatible API format.
"""

import logging
from typing import Any, Optional
from openai import OpenAI
from shared.config import settings

logger = logging.getLogger("nvidia_client")


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
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID (defaults to Llama 3.1 8B).
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
        
        Returns:
            OpenAI ChatCompletion response object.
        """
        model = model or settings.NIM_MODEL_8B

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
                return completion  # Returns an iterator

            logger.info(
                f"NIM completion: model={model}, "
                f"tokens={completion.usage.total_tokens if completion.usage else 'N/A'}"
            )
            return completion

        except Exception as e:
            logger.error(f"NVIDIA NIM API error: {e}")
            raise

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant for Indian government schemes.",
        model: str = None,
        max_tokens: int = 1024,
    ) -> str:
        """
        Simple text generation helper.
        
        Args:
            prompt: User prompt.
            system_prompt: System instruction.
            model: Model to use.
            max_tokens: Maximum output tokens.
        
        Returns:
            Generated text string.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = self.chat_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def generate_embedding(self, text: str, model: str = None) -> list[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: Input text to embed.
            model: Embedding model ID.
        
        Returns:
            List of floats representing the embedding vector.
        """
        model = model or settings.EMBEDDING_MODEL
        try:
            response = self.client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            raise

    def generate_embeddings_batch(self, texts: list[str], model: str = None) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        """
        model = model or settings.EMBEDDING_MODEL
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Batch embedding API error: {e}")
            raise


# ── Singleton client ──────────────────────────────────────────────────────────
nvidia_client = NVIDIAClient()


def get_nvidia_client() -> NVIDIAClient:
    """Get the singleton NVIDIA NIM client."""
    return nvidia_client
