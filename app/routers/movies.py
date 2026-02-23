from fastapi import APIRouter, HTTPException, Query

from app.models.media import Movie
from app.models.subtitle import SubtitleTrack, ExternalSubtitle
from app.services.radarr import radarr_client
from app.services.probe import probe_subtitles
from app.services.files import scan_external_subs

router = APIRouter(tags=["movies"])


@router.get("/movies", response_model=list[Movie])
async def list_movies(q: str = Query(default="", description="Search query")):
    try:
        if q:
            return await radarr_client.search(q)
        return await radarr_client.get_recent()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Radarr error: {e}")


@router.get("/movies/{movie_id}", response_model=Movie)
async def get_movie(movie_id: int):
    movie = await radarr_client.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("/movies/{movie_id}/tracks", response_model=list[SubtitleTrack])
async def get_movie_tracks(movie_id: int):
    movie = await radarr_client.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    if not movie.file_path:
        raise HTTPException(status_code=404, detail="No file associated with this movie")
    return await probe_subtitles(movie.file_path)


@router.get("/movies/{movie_id}/external-subs", response_model=list[ExternalSubtitle])
async def get_movie_external_subs(movie_id: int):
    movie = await radarr_client.get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    if not movie.folder_path:
        raise HTTPException(status_code=404, detail="No folder path for this movie")
    return scan_external_subs(movie.folder_path)
