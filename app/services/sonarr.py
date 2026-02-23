import time

import httpx

from app.config import Settings, load_settings
from app.models.media import Series, Episode


class SonarrClient:
    CACHE_TTL = 300  # 5 minutes

    def __init__(self) -> None:
        self._series_cache: list[dict] | None = None
        self._series_cache_time: float = 0
        self._episode_cache: dict[int, list[dict]] = {}
        self._episode_cache_time: dict[int, float] = {}
        self._settings: Settings | None = None

    def _get_settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def configure(self, settings: Settings) -> None:
        self._settings = settings
        self.clear_cache()

    def clear_cache(self) -> None:
        self._series_cache = None
        self._series_cache_time = 0
        self._episode_cache.clear()
        self._episode_cache_time.clear()

    def _client(self) -> httpx.AsyncClient:
        s = self._get_settings()
        return httpx.AsyncClient(
            base_url=s.sonarr_url.rstrip("/") + "/api/v3",
            headers={"X-Api-Key": s.sonarr_api_key},
            timeout=30,
        )

    async def _fetch_all_series(self) -> list[dict]:
        if self._series_cache is not None and (time.time() - self._series_cache_time) < self.CACHE_TTL:
            return self._series_cache
        async with self._client() as client:
            resp = await client.get("/series")
            resp.raise_for_status()
            self._series_cache = resp.json()
            self._series_cache_time = time.time()
            return self._series_cache

    async def _fetch_episodes(self, series_id: int) -> list[dict]:
        if series_id in self._episode_cache and (time.time() - self._episode_cache_time.get(series_id, 0)) < self.CACHE_TTL:
            return self._episode_cache[series_id]
        async with self._client() as client:
            resp = await client.get("/episode", params={"seriesId": series_id, "includeEpisodeFile": "true"})
            resp.raise_for_status()
            episodes = resp.json()
            self._episode_cache[series_id] = episodes
            self._episode_cache_time[series_id] = time.time()
            return episodes

    def _map_series(self, raw: dict) -> Series:
        stats = raw.get("statistics", {})
        return Series(
            id=raw["id"],
            title=raw.get("title", ""),
            year=raw.get("year", 0),
            path=self._get_settings().apply_path_mapping(raw.get("path", "")),
            season_count=stats.get("seasonCount", 0),
            episode_count=stats.get("episodeFileCount", 0),
            added=raw.get("added", ""),
        )

    def _map_episode(self, raw: dict, series_title: str = "") -> Episode:
        s = self._get_settings()
        ep_file = raw.get("episodeFile", {})
        file_path = ep_file.get("path", "")
        if not file_path:
            file_path = raw.get("episodeFilePath", "")
        return Episode(
            id=raw["id"],
            series_id=raw.get("seriesId", 0),
            series_title=series_title,
            season_number=raw.get("seasonNumber", 0),
            episode_number=raw.get("episodeNumber", 0),
            title=raw.get("title", ""),
            file_path=s.apply_path_mapping(file_path),
            has_file=raw.get("hasFile", False),
        )

    async def get_recent_series(self, limit: int = 20) -> list[Series]:
        series_list = await self._fetch_all_series()
        sorted_series = sorted(series_list, key=lambda s: s.get("added", ""), reverse=True)
        return [self._map_series(s) for s in sorted_series[:limit]]

    async def search_series(self, query: str) -> list[Series]:
        series_list = await self._fetch_all_series()
        q = query.lower()
        matches = [s for s in series_list if q in s.get("title", "").lower()]
        return [self._map_series(s) for s in matches[:50]]

    async def get_series_by_id(self, series_id: int) -> Series | None:
        series_list = await self._fetch_all_series()
        for s in series_list:
            if s["id"] == series_id:
                return self._map_series(s)
        return None

    async def get_episodes(self, series_id: int) -> list[Episode]:
        series = await self.get_series_by_id(series_id)
        series_title = series.title if series else ""
        episodes = await self._fetch_episodes(series_id)
        return [
            self._map_episode(ep, series_title)
            for ep in episodes
            if ep.get("hasFile")
        ]

    async def get_episode_by_id(self, episode_id: int) -> Episode | None:
        # First check already-cached episodes
        for series_id, episodes in self._episode_cache.items():
            if (time.time() - self._episode_cache_time.get(series_id, 0)) < self.CACHE_TTL:
                for ep in episodes:
                    if ep["id"] == episode_id:
                        series = await self.get_series_by_id(ep.get("seriesId", 0))
                        return self._map_episode(ep, series.title if series else "")

        # Fallback: fetch directly from Sonarr API
        try:
            async with self._client() as client:
                resp = await client.get(f"/episode/{episode_id}", params={"includeEpisodeFile": "true"})
                resp.raise_for_status()
                ep = resp.json()
                series = await self.get_series_by_id(ep.get("seriesId", 0))
                return self._map_episode(ep, series.title if series else "")
        except Exception:
            return None


sonarr_client = SonarrClient()
