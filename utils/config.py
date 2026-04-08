import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_env(path: str = ".env"):
    """Minimal .env loader - no dependency on python-dotenv."""
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    huggingface_api_key: str = field(default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY", ""))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    default_system_prompt: str = field(
        default_factory=lambda: os.getenv(
            "DEFAULT_SYSTEM_PROMPT",
            "Sos un asistente técnico experto. Respondé de forma concisa y precisa.",
        )
    )
    history_file: str = field(default_factory=lambda: os.getenv("HISTORY_FILE", "history.json"))

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Config":
        _load_env(env_file)
        return cls()