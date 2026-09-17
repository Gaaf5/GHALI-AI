from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


def create_llm(provider="ollama"):
    name = (provider or "ollama").lower().strip()
    if name == "ollama":
        return OllamaProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Unsupported LLM provider: {provider}")
