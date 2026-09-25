import os

from openai import OpenAI

from app.core.settings import OPENAI_MODEL
from .base import BaseLLM


class OpenAIProvider(BaseLLM):
    def __init__(self, model=None):
        self.model = model or OPENAI_MODEL
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=api_key)

    def chat(self, messages):
        tools = [{"type": "web_search"}] if os.getenv("GHALI_WEB_SEARCH", "true").lower() in {"1", "true", "yes", "on"} else None
        kwargs = {"model": self.model, "input": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        try:
            response = self.client.responses.create(**kwargs)
            return response.output_text
        except Exception as exc:
            # Keep the local app usable when OpenAI credits/quota are exhausted.
            # On a laptop with Ollama running, transparently fall back to the local model.
            msg = str(exc).lower()
            quota_error = "insufficient_quota" in msg or "credit" in msg and "remaining" in msg or "error code: 429" in msg
            if not quota_error:
                raise
            try:
                from .ollama_provider import OllamaProvider
                return OllamaProvider().chat(messages)
            except Exception as local_exc:
                raise RuntimeError(
                    "OpenAI quota is exhausted and the local Ollama fallback is unavailable. "
                    f"OpenAI error: {exc}; local fallback error: {local_exc}"
                ) from local_exc
