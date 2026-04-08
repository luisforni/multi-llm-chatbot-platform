import anthropic

from .base import BaseLLMProvider, Message


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"
    available_models = [
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ]

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        messages: list[Message],
        model: str = "claude-sonnet-4-6",
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> str:
        response = self.client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt or "You are a helpful assistant.",
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return response.content[0].text

    def list_models(self) -> list[str]:
        return self.available_models