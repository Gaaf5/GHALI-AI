from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .compatible_provider import MistralProvider, GroqProvider, OpenRouterProvider

def create_llm(provider=None):
    import os
    name=(provider or os.getenv("GHALI_LLM_PROVIDER","ollama")).lower().strip()
    if name=="ollama":
        return OllamaProvider()
    if name=="openai":
        return OpenAIProvider()
    if name=="gemini":
        return GeminiProvider()
    if name=="mistral":
        return MistralProvider()
    if name=="groq":
        return GroqProvider()
    if name=="openrouter":
        return OpenRouterProvider()
    if name in {"auto","fallback","router"}:
        from .router import build_router
        return build_router()
    raise ValueError(f"Unsupported LLM provider: {provider}")
