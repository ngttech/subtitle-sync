# Subtitle Sync — Implementation Plan

## Context

When downloading subtitles (e.g., Spanish) for movies/TV shows, the timing is often out of sync with the video. This app lets you select a movie or show from Radarr/Sonarr, extract its embedded subtitle track (e.g., English) as a timing reference, and automatically sync an external subtitle file to match. The synced file is saved next to the video, ready to use.

Inspired by [SubMerge](https://github.com/b4stOss/submerge) — we'll adapt its proven ffprobe/ffmpeg/ffsubsync patterns but add a web UI and Radarr/Sonarr integration.

## Tech Stack

- **Backend**: Python 3.10+ / FastAPI / Uvicorn
- **Frontend**: Vanilla HTML/JS with Pico CSS (no build step)
- **Subtitle tools**: ffmpeg/ffprobe (extraction), ffsubsync (sync), pysubs2 (file manipulation)
- **API clients**: httpx (async) for Radarr/Sonarr
- **Config**: JSON file edited via web UI
- **Cache**: In-memory with TTL (no database needed)

## Project Structure

```
subtitle-sync/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, static file serving
│   ├── config.py            # Settings load/save from settings.json
│   ├── services/
│   │   ├── __init__.py
│   │   ├── radarr.py        # Radarr API client (httpx async) + in-memory cache
│   │   ├── sonarr.py        # Sonarr API client (httpx async) + in-memory cache
│   │   ├── probe.py         # ffprobe wrapper — list subtitle tracks
│   │   ├── extract.py       # ffmpeg subtitle extraction
│   │   ├── sync.py          # ffsubsync wrapper (sub-to-sub & sub-to-audio)
│   │   └── files.py         # Scan folder for external .srt files
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test
│   │   ├── movies.py        # GET /api/movies, GET /api/movies/{id}/tracks
│   │   ├── shows.py         # GET /api/shows, episodes, tracks
│   │   ├── sync.py          # POST /api/sync, GET /api/sync/download/{file}
│   │   └── health.py        # GET /api/health (ffmpeg/ffsubsync check)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── settings.py      # Pydantic models for settings
│   │   ├── media.py         # Movie, Series, Episode models
│   │   └── subtitle.py      # SubtitleTrack, SyncRequest/Response models
│   └── static/
│       ├── index.html        # Single page app shell + Pico CSS
│       ├── css/app.css       # Minimal custom styles
│       └── js/
│           ├── app.js        # Hash-based router
│           ├── api.js        # fetch() wrapper for all API calls
│           └── pages/
│               ├── dashboard.js   # Health status, quick actions
│               ├── settings.js    # Settings form + test connections
│               ├── movies.js      # Movie list (searchable)
│               ├── movie.js       # Movie detail — tracks, external subs, sync
│               ├── shows.js       # Series list (searchable)
│               ├── episodes.js    # Episode list for a series
│               └── episode.js     # Episode detail — tracks, external subs, sync
├── data/                     # Temp files (extracted subs, sync output)
├── config/                   # Mounted volume for persistent settings
│   └── settings.json         # User settings (created at runtime)
├── Dockerfile                # Multi-stage build: python:3.11-slim + ffmpeg
├── docker-compose.yml        # Ready-to-use compose with volume mounts
├── .dockerignore
├── requirements.txt
├── run.py                    # Entry point: python run.py
└── pyproject.toml
```

## Key Features

### 1. Settings Page (with Path Mapping)
- Configure Radarr URL + API key, Sonarr URL + API key
- **Path mappings**: map Docker container paths to local paths (e.g., `/movies` → `D:\Movies`), or use matching mounts so no mapping is needed
  - Multiple mappings supported (movies, TV, etc.)
- "Test Connection" button for each service
- "Sync Library Now" button to trigger immediate refresh
- Persisted to `settings.json`

### 2. In-Memory Cache (simple, no database)
Radarr/Sonarr APIs return all items in a single call. Rather than hitting the API on every page load, we cache results in memory with a TTL.

**Strategy:**
- **First request**: Fetches all movies/shows from Radarr/Sonarr API (one call each), stores in memory
- **Cache TTL**: 5 minutes — subsequent requests within the window are instant
- **Manual refresh**: "Refresh" button clears the cache so the next request fetches fresh data
- **Default view**: Show only the **last 20** items (sorted by date added, most recent first)
- **Search**: User types a search query → backend filters the cached list → returns matches
- No database, no background tasks, no persistence — just a Python dict in memory

**How it works in the API clients:**
```python
class RadarrClient:
    _cache: list[dict] | None = None
    _cache_time: float = 0
    CACHE_TTL = 300  # 5 minutes

    async def get_movies(self) -> list[dict]:
        if self._cache and (time.time() - self._cache_time) < self.CACHE_TTL:
            return self._cache
        resp = await self.client.get("/movie")
        self._cache = [m for m in resp.json() if m.get("hasFile")]
        self._cache_time = time.time()
        return self._cache

    async def search_movies(self, query: str) -> list[dict]:
        movies = await self.get_movies()
        return [m for m in movies if query.lower() in m["title"].lower()]

    async def get_recent_movies(self, limit: int = 20) -> list[dict]:
        movies = await self.get_movies()
        return sorted(movies, key=lambda m: m.get("added", ""), reverse=True)[:limit]
```

### 3. Movie/Show Browser (minimal display — no posters)
**Movies page**: Searchable table with columns:
- Title | Year | File path
- Click a row → goes to sync page for that movie

**TV Shows page**: Searchable table with columns:
- Title | Year
- Click a row → shows seasons/episodes

**Episodes page**: Simple list grouped by season:
- Season X → Episode Y: "Episode Title" | File path
- Click an episode → goes to sync page

### 4. Subtitle Track Viewer
- Run ffprobe on the selected video file to list embedded subtitle tracks
- Show: language, codec, default/forced flags, text vs image-based
- Warn if only PGS (image-based) tracks exist — these can't be used as text reference

### 5. External Subtitle Source (Both Options)
- **Auto-detect**: Scan the video's folder for `.srt`/`.ass`/`.ssa`/`.vtt` files, list them for selection
- **Upload**: File upload input as a fallback when subs aren't in the video folder

### 6. Sync Engine
- **Primary mode (sub-to-sub)**: Extract embedded reference track → use ffsubsync to align external sub against it
- **Fallback mode (sub-to-audio)**: Align external sub directly against the video's audio track
- Save synced subtitle next to the video file (same folder, matching naming convention)
- Report the timing offset applied

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Check ffmpeg, ffprobe, ffsubsync availability |
| `GET` | `/api/settings` | Return settings (API keys masked) |
| `PUT` | `/api/settings` | Update settings |
| `POST` | `/api/settings/test` | Test Radarr/Sonarr connections |
| `POST` | `/api/cache/refresh` | Clear in-memory cache, next request fetches fresh data |
| `GET` | `/api/movies?q=search` | Recent 20 movies, or search if q provided (from cache) |
| `GET` | `/api/movies/{id}/tracks` | ffprobe subtitle tracks for a movie |
| `GET` | `/api/movies/{id}/external-subs` | List external .srt files in movie folder |
| `GET` | `/api/shows?q=search` | Recent 20 shows, or search if q provided (from cache) |
| `GET` | `/api/shows/{id}/episodes` | List episodes for a series (from Sonarr, cached) |
| `GET` | `/api/episodes/{id}/tracks` | ffprobe subtitle tracks for an episode |
| `GET` | `/api/episodes/{id}/external-subs` | List external subs in episode folder |
| `POST` | `/api/sync` | Run sync (multipart: video path, ref track, external sub file or path) |

## Implementation Order

### Phase 1 — Backend Foundation
1. Create `pyproject.toml` and `requirements.txt` with dependencies
2. `app/config.py` — settings model with path mappings, JSON load/save
3. `app/main.py` — FastAPI app factory, mount static files
4. `run.py` — entry point with uvicorn
5. `app/routers/health.py` + `app/services/health.py` — verify ffmpeg/ffsubsync installed

### Phase 2 — Settings & API Clients
6. `app/models/settings.py` — Pydantic request/response models
7. `app/routers/settings.py` — GET/PUT/test endpoints
8. `app/services/radarr.py` — async Radarr client with in-memory cache + path mapping
9. `app/services/sonarr.py` — async Sonarr client with in-memory cache + path mapping
10. `app/models/media.py` — Movie, Series, Episode models
11. `app/routers/movies.py` — recent 20 + search, movie detail
12. `app/routers/shows.py` — recent 20 + search, episodes list

### Phase 3 — Subtitle Pipeline
13. `app/services/probe.py` — ffprobe wrapper (adapted from SubMerge)
14. `app/services/extract.py` — ffmpeg extraction (adapted from SubMerge)
15. `app/services/sync.py` — ffsubsync wrapper (adapted from SubMerge)
16. `app/services/files.py` — scan folder for external subtitle files
17. `app/models/subtitle.py` — track info, sync request/response models
18. `app/routers/sync.py` — full sync endpoint: extract ref → ffsubsync → save output
19. Track endpoints on movies and episodes routers

### Phase 4 — Frontend
20. `index.html` — app shell with Pico CSS, nav bar, `<main id="app">`
21. `js/app.js` — hash router
22. `js/api.js` — API client
23. `pages/dashboard.js` — health status
24. `pages/settings.js` — settings form with path mapping rows, test buttons, refresh cache button
25. `pages/movies.js` — shows last 20, search box filters on type
26. `pages/movie.js` — track viewer + external sub picker + sync trigger
27. `pages/shows.js` — shows last 20, search box filters on type
28. `pages/episodes.js` — episode list grouped by season
29. `pages/episode.js` — same sync UI as movie detail

### Phase 5 — Docker
30. Create `Dockerfile` (python:3.11-slim + ffmpeg + pip install)
31. Create `docker-compose.yml` with media volume mounts and config volume
32. Create `.dockerignore` (data/, __pycache__, .git, etc.)
33. Update `app/config.py` to support `SUBTITLE_SYNC_CONFIG_DIR` env var for config path

### Phase 6 — Polish
34. Error handling — friendly messages for all failure modes
35. Loading states / spinners for async operations
36. Temp file cleanup (delete extracted refs after sync completes)
37. Edge cases: PGS-only warning, missing ffsubsync prompt, large offset warning

## Docker Deployment

### Dockerfile
- Base image: `python:3.11-slim`
- Install `ffmpeg` via apt
- Install Python deps from `requirements.txt` (includes ffsubsync)
- Copy app code
- Expose port 8765
- CMD: `python run.py`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data /app/config

EXPOSE 8765
CMD ["python", "run.py"]
```

### docker-compose.yml
The compose file maps the user's media library volumes so the container can access video files and save synced subtitles next to them. Settings persist via a config volume.

```yaml
services:
  subtitle-sync:
    build: .
    container_name: subtitle-sync
    ports:
      - "8765:8765"
    volumes:
      - ./config:/app/config          # Persistent settings
      - /path/to/movies:/movies       # Same mount as Radarr
      - /path/to/tv:/tv               # Same mount as Sonarr
    restart: unless-stopped
```

**Key design choice**: The media volume mounts should mirror Radarr/Sonarr's mounts. If Radarr sees movies at `/movies` inside its container, and the user mounts their host `D:\Movies` to `/movies` in Radarr, then Subtitle Sync should also mount `D:\Movies` to `/movies`. This way, **no path mapping is needed** — all three containers see the same paths. The path mapping feature in settings is still available for cases where mounts differ.

### Config changes for Docker
- `app/config.py` will look for settings at `/app/config/settings.json` (the mounted volume) so settings persist across container rebuilds
- The config path is configurable via `SUBTITLE_SYNC_CONFIG_DIR` env var (defaults to `./config` for local dev, `/app/config` in Docker)
- Temp files go to `/app/data` (ephemeral, no volume needed)

## Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Frontend | Vanilla JS + Pico CSS | ~5 pages, no complex state — zero build step, no node_modules |
| HTTP client | httpx (async) | Native async for FastAPI, connection pooling |
| Subprocess calls | `asyncio.to_thread()` | Simple; preserves SubMerge's clean synchronous logic |
| Settings storage | JSON file | Local tool; users configure via UI, not env vars |
| Sync default | Sub-to-sub | Faster, more reliable than audio matching |
| Port | 8765 | Avoids Radarr (7878) and Sonarr (8989) |
| Path mapping | Configurable in settings UI | Docker paths ≠ Windows paths; user defines mappings |

## Dependencies

**Python packages**: `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic`, `pydantic-settings`, `python-multipart`, `ffsubsync`, `pysubs2`

**System requirements**: `ffmpeg` (includes ffprobe), Python 3.10+

## Verification Plan

1. **Health check**: Start the app, visit `http://localhost:8765` — dashboard should show green for ffmpeg/ffsubsync
2. **Settings**: Configure Radarr/Sonarr URLs, API keys, and path mappings — "Test Connection" should show success
3. **Movie list**: Navigate to Movies — should see the full library from Radarr with corrected paths
4. **Track probe**: Click a movie — should see its embedded subtitle tracks listed
5. **External subs**: Same page should list any .srt files found in the movie's folder
6. **Sync test**: Select a reference track, pick an external sub, click Sync — verify:
   - ffsubsync runs and reports offset
   - Synced file appears next to the video
   - Subtitle timing matches the embedded reference
7. **TV show flow**: Same flow through Shows → Series → Episode → Sync
8. **Docker build**: Run `docker compose up --build` — container starts, ffmpeg/ffsubsync available, media volumes accessible, settings persist across restarts
