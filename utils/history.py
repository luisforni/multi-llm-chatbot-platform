import json
from datetime import datetime
from pathlib import Path

from providers.base import Message


class HistoryManager:
    """
    Persists conversation history to a JSON file.
    Each session is keyed by timestamp on init.
    """

    def __init__(self, path: str = "history.json"):
        self.path = Path(path)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages: list[Message] = []
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return {}

    def _save(self):
        self._data[self.session_id] = {
            "timestamp": self.session_id,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
        }
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def add(self, role: str, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self._save()
        return msg

    def clear(self):
        self.messages = []
        self._data.pop(self.session_id, None)
        if self._data:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        elif self.path.exists():
            self.path.unlink()

    def list_sessions(self) -> list[str]:
        return list(self._data.keys())

    def load_session(self, session_id: str):
        session = self._data.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        self.messages = [Message(**m) for m in session["messages"]]
        self.session_id = session_id

    def __len__(self):
        return len(self.messages)