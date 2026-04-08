from providers import (
    AnthropicProvider,
    BaseLLMProvider,
    HuggingFaceProvider,
    OllamaProvider,
    OpenAIProvider,
)
from utils.config import Config


class ProviderRegistry:
    """
    Central registry that builds providers lazily from config.
    Usage:
        registry = ProviderRegistry(config)
        provider = registry.get("ollama")
    """

    def __init__(self, config: Config):
        self._config = config
        self._cache: dict[str, BaseLLMProvider] = {}

    def get(self, name: str) -> BaseLLMProvider:
        if name in self._cache:
            return self._cache[name]

        provider = self._build(name)
        self._cache[name] = provider
        return provider

    def _build(self, name: str) -> BaseLLMProvider:
        cfg = self._config
        match name:
            case "anthropic":
                return AnthropicProvider(api_key=cfg.anthropic_api_key or None)
            case "openai":
                return OpenAIProvider(api_key=cfg.openai_api_key or None)
            case "ollama":
                return OllamaProvider(base_url=cfg.ollama_base_url)
            case "huggingface":
                return HuggingFaceProvider(api_key=cfg.huggingface_api_key or None)
            case _:
                raise ValueError(f"Unknown provider: '{name}'. Available: anthropic, openai, ollama, huggingface")

    def available(self) -> list[str]:
        return ["anthropic", "openai", "ollama", "huggingface"]