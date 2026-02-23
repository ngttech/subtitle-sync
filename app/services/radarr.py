import time

import httpx

from app.config import Settings, load_settings
from app.models.media import Movie


class RadarrClient:
    CACHE_TTL = 300  # 5 minutes

    def __init__(self) -> None:
        self._cache: list[dict] | None = None
        self._cache_time: float = 0
        self._settings: Settings | None = None

    def _get_settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def configure(self, settings: Settings) -> None:
        self._settings = settings
        self.clear_cache()

    def clear_cache(self) -> None:
        self._cache = None
        self._cache_time = 0

    def _client(self) -> httpx.AsyncClient:
        s = self._get_settings()
        return httpx.AsyncClient(
            base_url=s.radarr_url.rstrip("/") + "/api/v3",
            headers={"X-Api-Key": s.radarr_api_key},
            timeout=30,
        )

    async def _fetch_all(self) -> list[dict]:
        if self._cache is not None and (time.time() - self._cache_time) < self.CACHE_TTL:
            return self._cache
        async with self._client() as client:
            resp = await client.get("/movie")
            resp.raise_for_status()
            self._cache = [m for m in resp.json() if m.get("hasFile")]
            self._cache_time = time.time()
            return self._cache

    def _map_movie(self, raw: dict) -> Movie:
        s = self._get_settings()
        movie_file = raw.get("movieFile", {})
        file_path = movie_file.get("path", "")
        folder_path = raw.get("path", "")
        return Movie(
            id=raw["id"],
            title=raw.get("title", ""),
            year=raw.get("year", 0),
            file_path=s.apply_path_mapping(file_path),
            folder_path=s.apply_path_mapping(folder_path),
            has_file=raw.get("hasFile", False),
            size_on_disk=raw.get("sizeOnDisk", 0),
            added=raw.get("added", ""),
        )

    async def get_recent(self, limit: int = 20) -> list[Movie]:
        movies = await self._fetch_all()
        sorted_movies = sorted(movies, key=lambda m: m.get("added", ""), reverse=True)
        return [self._map_movie(m) for m in sorted_movies[:limit]]

    async def search(self, query: str) -> list[Movie]:
        movies = await self._fetch_all()
        q = query.lower()
        matches = [m for m in movies if q in m.get("title", "").lower()]
        return [self._map_movie(m) for m in matches[:50]]

    async def get_by_id(self, movie_id: int) -> Movie | None:
        movies = await self._fetch_all()
        for m in movies:
            if m["id"] == movie_id:
                return self._map_movie(m)
        return None


radarr_client = RadarrClient()
