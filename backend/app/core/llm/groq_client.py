import logging
import random
import re
from typing import Dict, Any, List, Optional
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3-groq-70b-8192-tool-use-preview",
]


class GroqClient:
    """Manages Groq API interactions with retry logic and model fallback."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.models = AVAILABLE_MODELS
        self.current_model_index = 0

    def _get_random_model(self) -> str:
        return random.choice(self.models)

    def _get_next_fallback_model(self, failed_model: str) -> str:
        available = [m for m in self.models if m != failed_model]
        return random.choice(available) if available else self.models[0]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Make a single API request to Groq."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content
        content = clean_llm_response(content)

        return {
            "content": content,
            "model_used": model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke the LLM with automatic model selection and fallback."""
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        selected_model = model or self._get_random_model()
        logger.info(f"Using model: {selected_model}")

        try:
            return await self._make_request(messages, selected_model, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Model {selected_model} failed: {e}. Trying fallback...")
            fallback_model = self._get_next_fallback_model(selected_model)
            logger.info(f"Falling back to: {fallback_model}")
            try:
                return await self._make_request(messages, fallback_model, temperature, max_tokens)
            except Exception as e2:
                logger.error(f"Fallback model {fallback_model} also failed: {e2}")
                raise

    async def invoke_with_json(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke LLM expecting JSON response."""
        json_system = (system_prompt or "") + "\nRespond only with valid JSON. No markdown, no explanation."
        return await self.invoke(messages, json_system, temperature, model=model)


def clean_llm_response(text: str) -> str:
    """Remove thinking tags and markdown artifacts from LLM output."""
    if not text:
        return text

    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    text = text.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.split("\n")
        if len(lines) > 2:
            text = "\n".join(lines[1:-1])

    return text.strip()


_groq_client: GroqClient | None = None


def get_groq_client() -> GroqClient:
    """Get or create Groq client instance."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
