from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


def create_llm(provider=None):
    import os
    name = (provider or os.getenv("GHALI_LLM_PROVIDER", "ollama")).lower().strip()
    if name == "ollama":
        return OllamaProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unsupported LLM provider: {provider}")
