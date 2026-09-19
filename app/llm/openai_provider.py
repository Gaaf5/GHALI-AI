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
        response = self.client.responses.create(**kwargs)
        return response.output_text
