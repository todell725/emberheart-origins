"""
LLM Client - Abstraction layer for Ollama integration
Handles all communication with local LLM models
"""
import requests
import json
import logging
import aiohttp
from typing import Optional, Dict, Any, Generator

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API"""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.1"):
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        logger.info(f"Initialized Ollama client: {base_url} (model: {default_model})")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        stop: Optional[list] = None,
        system: Optional[str] = None
    ) -> str:
        """
        Generate a completion from the LLM

        Args:
            prompt: The input prompt
            model: Model to use (defaults to self.default_model)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            num_ctx: Size of the context window
            stop: List of stop sequences
            system: System prompt

        Returns:
            Generated text
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if num_ctx:
            payload["options"]["num_ctx"] = num_ctx

        if stop:
            payload["options"]["stop"] = stop

        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "")

            logger.debug(f"Generated {len(generated_text)} chars with model {model}")
            return generated_text

        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise ConnectionError(f"Failed to connect to Ollama: {e}")

    async def async_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        stop: Optional[list] = None,
        system: Optional[str] = None
    ) -> str:
        """
        Async version of generate() — safe to call from the Discord event loop.
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if num_ctx:
            payload["options"]["num_ctx"] = num_ctx
        if stop:
            payload["options"]["stop"] = stop
        if system:
            payload["system"] = system

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()
                    generated_text = result.get("response", "")
                    logger.debug(f"[async] Generated {len(generated_text)} chars with model {model}")
                    return generated_text
        except Exception as e:
            logger.error(f"Async Ollama API error: {e}")
            raise ConnectionError(f"Failed to connect to Ollama: {e}")

    def generate_streaming(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming completion from the LLM

        Args:
            prompt: The input prompt
            model: Model to use
            temperature: Sampling temperature
            system: System prompt

        Yields:
            Text chunks as they're generated
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]

        except requests.RequestException as e:
            logger.error(f"Ollama streaming error: {e}")
            raise ConnectionError(f"Failed to stream from Ollama: {e}")

    def list_models(self) -> list:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except requests.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
