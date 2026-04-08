from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


class BaseLLMProvider(ABC):
    name: str
    available_models: list[str]

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        model: str,
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> str: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...

    def __repr__(self):
        return f"<{self.__class__.__name__} provider='{self.name}'>"