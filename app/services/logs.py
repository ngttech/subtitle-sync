import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_data_dir

LOG_FILENAME = "subtitle_sync.log"


def _log_path() -> Path:
    return get_data_dir() / LOG_FILENAME


def log_action(action: str, **kwargs) -> None:
    """Append one log entry. Thread-safe via append mode."""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "action": action, **kwargs}
    path = _log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_logs(limit: int = 200) -> list[dict]:
    """Read last N entries, newest first."""
    path = _log_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def clear_logs() -> None:
    path = _log_path()
    if path.exists():
        path.unlink()


def get_log_path() -> Path:
    return _log_path()
