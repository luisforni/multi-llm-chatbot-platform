import httpx

from .base import BaseLLMProvider, Message


class OllamaProvider(BaseLLMProvider):
    """
    Runs against a local Ollama instance (http://localhost:11434).
    Models are pulled on-demand: `ollama pull llama3.2`
    """

    name = "ollama"
    available_models = ["llama3.2", "mistral", "phi3", "qwen2.5", "gemma2"]

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        messages: list[Message],
        model: str = "llama3.2",
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {"temperature": temperature},
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def list_models(self) -> list[str]:
        """Fetches models actually installed in the local Ollama instance."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except httpx.ConnectError:
            return []

    def pull_model(self, model: str) -> None:
        """Pull a model from Ollama registry."""
        print(f"Pulling {model}... (this may take a while)")
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/pull",
            json={"name": model},
            timeout=None,
        ) as r:
            for line in r.iter_lines():
                if '"status"' in line:
                    import json
                    data = json.loads(line)
                    print(f"\r  {data.get('status', '')} {data.get('completed', '')}", end="")
        print("\nDone.")