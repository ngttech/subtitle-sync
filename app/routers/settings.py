import httpx
from fastapi import APIRouter

from app.config import load_settings, save_settings, Settings, PathMapping
from app.models.settings import (
    SettingsRequest,
    SettingsResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    PathMappingModel,
)
from app.services.radarr import radarr_client
from app.services.sonarr import sonarr_client

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    s = load_settings()
    return SettingsResponse(
        radarr_url=s.radarr_url,
        radarr_api_key_set=bool(s.radarr_api_key),
        sonarr_url=s.sonarr_url,
        sonarr_api_key_set=bool(s.sonarr_api_key),
        path_mappings=[
            PathMappingModel(from_path=m.from_path, to_path=m.to_path)
            for m in s.path_mappings
        ],
        ai_provider=s.ai_provider,
        openai_api_key_set=bool(s.openai_api_key),
        anthropic_api_key_set=bool(s.anthropic_api_key),
        openai_model=s.openai_model,
        anthropic_model=s.anthropic_model,
        default_language=s.default_language,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsRequest):
    current = load_settings()

    radarr_key = req.radarr_api_key if req.radarr_api_key else current.radarr_api_key
    sonarr_key = req.sonarr_api_key if req.sonarr_api_key else current.sonarr_api_key
    openai_key = req.openai_api_key if req.openai_api_key else current.openai_api_key
    anthropic_key = req.anthropic_api_key if req.anthropic_api_key else current.anthropic_api_key

    new_settings = Settings(
        radarr_url=req.radarr_url,
        radarr_api_key=radarr_key,
        sonarr_url=req.sonarr_url,
        sonarr_api_key=sonarr_key,
        path_mappings=[
            PathMapping(from_path=m.from_path, to_path=m.to_path)
            for m in req.path_mappings
        ],
        ai_provider=req.ai_provider,
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        openai_model=req.openai_model,
        anthropic_model=req.anthropic_model,
        default_language=req.default_language,
    )
    save_settings(new_settings)

    radarr_client.configure(new_settings)
    sonarr_client.configure(new_settings)

    return SettingsResponse(
        radarr_url=new_settings.radarr_url,
        radarr_api_key_set=bool(new_settings.radarr_api_key),
        sonarr_url=new_settings.sonarr_url,
        sonarr_api_key_set=bool(new_settings.sonarr_api_key),
        path_mappings=[
            PathMappingModel(from_path=m.from_path, to_path=m.to_path)
            for m in new_settings.path_mappings
        ],
        ai_provider=new_settings.ai_provider,
        openai_api_key_set=bool(new_settings.openai_api_key),
        anthropic_api_key_set=bool(new_settings.anthropic_api_key),
        openai_model=new_settings.openai_model,
        anthropic_model=new_settings.anthropic_model,
        default_language=new_settings.default_language,
    )


@router.post("/settings/test", response_model=TestConnectionResponse)
async def test_connection(req: TestConnectionRequest):
    url = req.url.rstrip("/")

    # Use stored key if the frontend sends the placeholder
    api_key = req.api_key
    if not api_key or api_key == "(current)":
        current = load_settings()
        api_key = current.radarr_api_key if req.service == "radarr" else current.sonarr_api_key

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if req.service in ("radarr", "sonarr"):
                resp = await client.get(
                    f"{url}/api/v3/system/status",
                    headers={"X-Api-Key": api_key},
                )
            else:
                return TestConnectionResponse(success=False, message=f"Unknown service: {req.service}")

            if resp.status_code == 200:
                data = resp.json()
                version = data.get("version", "unknown")
                return TestConnectionResponse(
                    success=True,
                    message=f"Connected to {req.service.title()} v{version}",
                )
            elif resp.status_code == 401:
                return TestConnectionResponse(success=False, message="Invalid API key")
            else:
                return TestConnectionResponse(
                    success=False, message=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
    except httpx.ConnectError:
        return TestConnectionResponse(success=False, message=f"Cannot connect to {url}")
    except httpx.TimeoutException:
        return TestConnectionResponse(success=False, message="Connection timed out")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e)[:200])


@router.post("/cache/refresh")
async def refresh_cache():
    radarr_client.clear_cache()
    sonarr_client.clear_cache()
    return {"message": "Cache cleared"}
