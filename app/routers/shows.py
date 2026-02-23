from fastapi import APIRouter, HTTPException, Query

from app.models.media import Series, Episode
from app.models.subtitle import SubtitleTrack, ExternalSubtitle
from app.services.sonarr import sonarr_client
from app.services.probe import probe_subtitles
from app.services.files import scan_external_subs

router = APIRouter(tags=["shows"])


@router.get("/shows", response_model=list[Series])
async def list_shows(q: str = Query(default="", description="Search query")):
    try:
        if q:
            return await sonarr_client.search_series(q)
        return await sonarr_client.get_recent_series()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sonarr error: {e}")


@router.get("/shows/{series_id}", response_model=Series)
async def get_show(series_id: int):
    series = await sonarr_client.get_series_by_id(series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


@router.get("/shows/{series_id}/episodes", response_model=list[Episode])
async def list_episodes(series_id: int):
    try:
        return await sonarr_client.get_episodes(series_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sonarr error: {e}")


@router.get("/episodes/{episode_id}", response_model=Episode)
async def get_episode(episode_id: int):
    episode = await sonarr_client.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.get("/episodes/{episode_id}/tracks", response_model=list[SubtitleTrack])
async def get_episode_tracks(episode_id: int):
    episode = await sonarr_client.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not episode.file_path:
        raise HTTPException(status_code=404, detail="No file for this episode")
    return await probe_subtitles(episode.file_path)


@router.get("/episodes/{episode_id}/external-subs", response_model=list[ExternalSubtitle])
async def get_episode_external_subs(episode_id: int):
    episode = await sonarr_client.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not episode.file_path:
        raise HTTPException(status_code=404, detail="No file for this episode")
    from pathlib import Path
    video_path = Path(episode.file_path)
    return scan_external_subs(str(video_path.parent), video_stem=video_path.stem)
