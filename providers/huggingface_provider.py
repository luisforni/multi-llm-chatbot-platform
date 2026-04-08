import httpx

from .base import BaseLLMProvider, Message


class HuggingFaceProvider(BaseLLMProvider):
    """
    Uses Hugging Face Inference API (hosted models).
    Free tier available, some models behind Pro.
    """

    name = "huggingface"
    available_models = [
        "mistralai/Mistral-7B-Instruct-v0.3",
        "microsoft/Phi-3-mini-4k-instruct",
        "HuggingFaceH4/zephyr-7b-beta",
        "tiiuae/falcon-7b-instruct",
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.base_url = "https://api-inference.huggingface.co/models"

    def chat(
        self,
        messages: list[Message],
        model: str = "mistralai/Mistral-7B-Instruct-v0.3",
        system_prompt: str = "",
        temperature: float = 0.7,
    ) -> str:
        # Build prompt in chat-ml format
        prompt = ""
        if system_prompt:
            prompt += f"<|system|>\n{system_prompt}\n"
        for m in messages:
            tag = "user" if m.role == "user" else "assistant"
            prompt += f"<|{tag}|>\n{m.content}\n"
        prompt += "<|assistant|>\n"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = httpx.post(
            f"{self.base_url}/{model}",
            headers=headers,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": temperature,
                    "return_full_text": False,
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data[0].get("generated_text", "").strip()
        return str(data)

    def list_models(self) -> list[str]:
        return self.available_models