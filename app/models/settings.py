from pydantic import BaseModel


class PathMappingModel(BaseModel):
    from_path: str
    to_path: str


class SettingsRequest(BaseModel):
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    path_mappings: list[PathMappingModel] = []
    ai_provider: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""


class SettingsResponse(BaseModel):
    radarr_url: str = ""
    radarr_api_key_set: bool = False
    sonarr_url: str = ""
    sonarr_api_key_set: bool = False
    path_mappings: list[PathMappingModel] = []
    ai_provider: str = ""
    openai_api_key_set: bool = False
    anthropic_api_key_set: bool = False


class TestConnectionRequest(BaseModel):
    service: str  # "radarr" or "sonarr"
    url: str
    api_key: str


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
