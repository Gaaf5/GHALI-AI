import os
from .base import BaseLLM

class FallbackRouter(BaseLLM):
    def __init__(self, providers):
        self.providers=providers
        self.model=" -> ".join(getattr(p,"label",getattr(p,"model","unknown")) for p in providers) or "none"

    @staticmethod
    def _retryable(exc):
        msg=str(exc).lower()
        return any(x in msg for x in (
            "429","rate limit","resource_exhausted","quota","credit_balance_exhausted",
            "insufficient_quota","too many requests","credits","temporarily unavailable",
            "service unavailable","timeout"
        ))

    def chat(self, messages):
        errors=[]
        for provider in self.providers:
            try:
                return provider.chat(messages)
            except Exception as exc:
                errors.append(f"{getattr(provider,'label',getattr(provider,'model','provider'))}: {exc}")
                if not self._retryable(exc):
                    continue
        if not errors:
            raise RuntimeError("No LLM providers are configured.")
        raise RuntimeError("All configured LLM providers failed. " + " | ".join(errors))

def build_router():
    from .gemini_provider import GeminiProvider
    from .compatible_provider import MistralProvider, GroqProvider, OpenRouterProvider
    from .openai_provider import OpenAIProvider
    from .ollama_provider import OllamaProvider

    factories={
        "gemini":GeminiProvider,
        "mistral":MistralProvider,
        "groq":GroqProvider,
        "openrouter":OpenRouterProvider,
        "openai":OpenAIProvider,
        "ollama":OllamaProvider,
    }
    order=os.getenv("GHALI_LLM_FALLBACKS",
                    "gemini,mistral,groq,openrouter,openai,ollama").split(",")
    providers=[]
    for name in [x.strip().lower() for x in order if x.strip()]:
        factory=factories.get(name)
        if not factory:
            continue
        try:
            providers.append(factory())
        except Exception:
            continue
    return FallbackRouter(providers)
