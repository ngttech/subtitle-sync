import json
import os
from pathlib import Path
from pydantic import BaseModel


class PathMapping(BaseModel):
    from_path: str
    to_path: str


class Settings(BaseModel):
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    path_mappings: list[PathMapping] = []
    ai_provider: str = ""  # "openai" or "anthropic" (empty = not configured)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    def apply_path_mapping(self, path: str) -> str:
        for mapping in self.path_mappings:
            if path.startswith(mapping.from_path):
                return path.replace(mapping.from_path, mapping.to_path, 1)
        return path


def _config_dir() -> Path:
    env = os.environ.get("SUBTITLE_SYNC_CONFIG_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "config"


def _config_path() -> Path:
    return _config_dir() / "settings.json"


def _data_dir() -> Path:
    env = os.environ.get("SUBTITLE_SYNC_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data"


def get_data_dir() -> Path:
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_settings() -> Settings:
    path = _config_path()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return Settings(**data)
    return Settings()


def save_settings(settings: Settings) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
