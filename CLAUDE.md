# Subtitle Sync

## Project Overview
A web app that syncs external subtitle files to match embedded subtitle timing in video files. Integrates with Radarr/Sonarr for media library browsing. Uses ffmpeg/ffprobe for extraction and ffsubsync for timing alignment.

## Tech Stack
- **Backend**: Python 3.10+ / FastAPI / Uvicorn (port 8765)
- **Frontend**: Vanilla HTML/JS with Pico CSS (dark theme, no build step)
- **Tools**: ffmpeg, ffprobe, ffsubsync, pysubs2
- **API clients**: httpx (async) for Radarr/Sonarr v3 API
- **Config**: JSON file at `config/settings.json` (or `SUBTITLE_SYNC_CONFIG_DIR` env var)

## Project Structure
```
app/
├── main.py              # FastAPI app factory, mounts static files, includes all routers
├── config.py            # Settings model, load/save JSON, path mapping, data dir
├── services/            # Business logic
│   ├── radarr.py        # Radarr client with 5-min in-memory cache
│   ├── sonarr.py        # Sonarr client with 5-min in-memory cache
│   ├── probe.py         # ffprobe wrapper → SubtitleTrack list
│   ├── extract.py       # ffmpeg subtitle extraction to temp .srt
│   ├── sync.py          # ffsubsync wrapper (sub-to-sub & sub-to-audio)
│   └── files.py         # Scan folder for external subtitle files
├── routers/             # API endpoints (all prefixed /api)
│   ├── health.py        # GET /api/health
│   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test, POST /api/cache/refresh
│   ├── movies.py        # GET /api/movies, /api/movies/{id}, /tracks, /external-subs
│   ├── shows.py         # GET /api/shows, /api/shows/{id}/episodes, /api/episodes/{id}/*
│   └── sync.py          # POST /api/sync (multipart form)
├── models/              # Pydantic models
│   ├── settings.py      # SettingsRequest/Response, TestConnection models
│   ├── media.py         # Movie, Series, Episode
│   └── subtitle.py      # SubtitleTrack, ExternalSubtitle, SyncRequest/Response
└── static/              # Frontend (served at / and /static)
    ├── index.html       # SPA shell with Pico CSS
    ├── css/app.css      # Custom styles
    └── js/
        ├── app.js       # Hash-based SPA router
        ├── api.js       # fetch() wrapper (API object)
        └── pages/       # One file per page (dashboard, settings, movies, movie, shows, episodes, episode)
```

## Key Patterns

### Caching
- Radarr/Sonarr clients use in-memory cache with 5-minute TTL
- Cache stores raw API responses; mapping happens on read
- `POST /api/cache/refresh` clears both caches
- No database, no background tasks

### Path Mapping
- `config.py` → `Settings.apply_path_mapping(path)` replaces from_path prefix with to_path
- Applied when mapping raw Radarr/Sonarr responses to our models
- Needed when container paths differ from local paths

### Subprocess Calls
- ffprobe, ffmpeg, ffsubsync all run via `subprocess.run()` wrapped in `asyncio.to_thread()`
- Temp files (extracted references) go to `data/` dir and are cleaned up after sync

### Frontend Routing
- Hash-based: `#/movies`, `#/movie/{id}`, `#/shows`, `#/episodes/{seriesId}`, `#/episode/{id}`, `#/settings`
- Each page is a function in `pages/*.js` that receives `(container, id)` and renders into it
- `renderTracks()` and `renderExternalSubs()` are shared helpers defined in `movie.js`, reused by `episode.js`

### Sync Flow
1. User selects reference track (embedded) + external subtitle (from folder or upload)
2. `POST /api/sync` with multipart form data
3. Backend extracts reference track via ffmpeg → temp .srt
4. Runs ffsubsync: reference .srt + external sub → synced output
5. Saves output next to video file as `{video_stem}.{language}.srt`
6. Cleans up temp files
7. Returns success/failure, offset in ms, output path

## Environment Variables
- `SUBTITLE_SYNC_CONFIG_DIR` — directory for settings.json (default: `./config`)
- `SUBTITLE_SYNC_DATA_DIR` — directory for temp files (default: `./data`)
- `SUBTITLE_SYNC_DEV` — set to `0` to disable uvicorn reload (default: `1`)

## Running
```bash
pip install -r requirements.txt
python run.py
# → http://localhost:8765
```

## Docker
```bash
# Edit docker-compose.yml to set media volume paths first
docker compose up --build
```

## Dependencies
- Python: fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings, python-multipart, ffsubsync, pysubs2
- System: ffmpeg (includes ffprobe)

## Important Notes
- Radarr/Sonarr API v3 is used (both use same `/api/v3` pattern)
- Only movies/episodes with files (`hasFile: true`) are shown
- PGS/image-based subtitle tracks are detected and disabled for sub-to-sub sync
- The sync router accepts both file upload and file path for external subtitles
- Settings API never returns raw API keys — only a boolean `_key_set` flag
- Test connection endpoint uses stored key when frontend sends empty or `(current)` placeholder
