import requests

from app.core.settings import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OLLAMA_TEMPERATURE,
    OLLAMA_NUM_PREDICT,
)
from .base import BaseLLM


class OllamaProvider(BaseLLM):

    def __init__(self, model=None, url=None):
        self.model = model or OLLAMA_MODEL
        self.url = url or OLLAMA_URL

    def chat(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": OLLAMA_NUM_PREDICT,
                "temperature": OLLAMA_TEMPERATURE,
            },
        }

        response = requests.post(self.url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data["message"]["content"]
