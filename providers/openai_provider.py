from openai import OpenAI

from .base import BaseLLMProvider, Message


class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    available_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]

    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key)

    def chat(
        self,
        messages: list[Message],
        model: str = "gpt-4o-mini",
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> str:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted += [{"role": m.role, "content": m.content} for m in messages]

        response = self.client.chat.completions.create(
            model=model,
            messages=formatted,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def list_models(self) -> list[str]:
        return self.available_models