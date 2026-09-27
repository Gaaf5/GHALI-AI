import os
from openai import OpenAI
from .base import BaseLLM

class CompatibleProvider(BaseLLM):
    def __init__(self, env_key, default_model, base_url, label, model_env=None, extra_headers=None):
        self.label=label
        self.api_key=os.getenv(env_key)
        self.model=os.getenv(model_env or "", default_model) if model_env else default_model
        if not self.api_key:
            raise RuntimeError(f"{env_key} is not configured")
        self.client=OpenAI(api_key=self.api_key, base_url=base_url, default_headers=extra_headers or {})

    def chat(self, messages):
        response=self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=900,
        )
        text=response.choices[0].message.content if response.choices else None
        if not text:
            raise RuntimeError(f"{self.label} returned an empty response")
        return text

class MistralProvider(CompatibleProvider):
    def __init__(self):
        super().__init__("MISTRAL_API_KEY","mistral-small-latest","https://api.mistral.ai/v1","Mistral","MISTRAL_MODEL")

class GroqProvider(CompatibleProvider):
    def __init__(self):
        super().__init__("GROQ_API_KEY","qwen/qwen3.8-27b","https://api.groq.com/openai/v1","Groq","GROQ_MODEL")

class OpenRouterProvider(CompatibleProvider):
    def __init__(self):
        super().__init__("OPENROUTER_API_KEY","openrouter/free","https://openrouter.ai/api/v1","OpenRouter","OPENROUTER_MODEL",
                         {"HTTP-Referer":"https://ghali-ai.onrender.com","X-Title":"GHALI AI"})
