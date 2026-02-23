# Subtitle Sync

## Project Overview
A web app that syncs external subtitle files to match embedded subtitle timing in video files. Integrates with Radarr/Sonarr for media library browsing. Uses ffmpeg/ffprobe for extraction and ffsubsync/alass for timing alignment. Supports AI-powered subtitle translation via OpenAI or Anthropic.

## Tech Stack
- **Backend**: Python 3.10+ / FastAPI / Uvicorn (port 8765)
- **Frontend**: Vanilla HTML/JS with Pico CSS (dark theme, no build step)
- **Tools**: ffmpeg, ffprobe, ffsubsync, alass, pysubs2
- **AI**: openai SDK, anthropic SDK, langdetect (for translation feature)
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
│   ├── sync.py          # ffsubsync + alass wrappers (sub-to-sub & sub-to-audio)
│   ├── translate.py     # AI translation service (OpenAI + Anthropic)
│   └── files.py         # Scan folder for external subtitle files
├── routers/             # API endpoints (all prefixed /api)
│   ├── health.py        # GET /api/health
│   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test, POST /api/cache/refresh
│   ├── movies.py        # GET /api/movies, /api/movies/{id}, /tracks, /external-subs
│   ├── shows.py         # GET /api/shows, /api/shows/{id}/episodes, /api/episodes/{id}/*
│   ├── sync.py          # POST /api/sync (multipart form)
│   └── translate.py     # POST /api/translate (multipart form)
├── models/              # Pydantic models
│   ├── settings.py      # SettingsRequest/Response, TestConnection models
│   ├── media.py         # Movie, Series, Episode
│   └── subtitle.py      # SubtitleTrack, ExternalSubtitle, SyncRequest/Response, TranslateResponse
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
- ffprobe, ffmpeg, ffsubsync, alass all run via `subprocess.run()` wrapped in `asyncio.to_thread()`
- Temp files (extracted references) go to `data/` dir and are cleaned up after sync

### Frontend Routing
- Hash-based: `#/movies`, `#/movie/{id}`, `#/shows`, `#/episodes/{seriesId}`, `#/episode/{id}`, `#/settings`
- Each page is a function in `pages/*.js` that receives `(container, id)` and renders into it
- `renderTracks()` and `renderExternalSubs()` are shared helpers defined in `movie.js`, reused by `episode.js`
- `renderTracks(container, tracks, videoPath, onTranslated)` — accepts video path and callback for translate button

### Sync Flow
1. User selects reference track (embedded) + external subtitle (from folder or upload)
2. User picks sync engine (ffsubsync or alass) and sync mode
3. `POST /api/sync` with multipart form data (includes `sync_engine` param)
4. Backend extracts reference track via ffmpeg → temp .srt
5. Runs ffsubsync or alass: reference .srt + external sub → synced output
6. Saves output next to video file as `{video_stem}.{language}.srt`
7. Cleans up temp files
8. Returns success/failure, offset in ms, output path

### Sync Engines
- **ffsubsync**: Default engine, uses `--gss` flag. Best for same-language sync.
- **alass**: Rust-based, faster, better at cross-language subtitle sync. Binary installed as `alass-cli`.

### AI Translation Flow
1. User clicks "Translate" button on an embedded text-based track
2. Prompted for target language code (e.g. es, pt, fr)
3. `POST /api/translate` with video_path, track_index, target_language
4. Backend extracts track via ffmpeg, loads with pysubs2
5. Auto-detects source language via langdetect
6. Sends subtitle lines in batches of 50 to OpenAI or Anthropic
7. Saves translated file next to video as `{video_stem}.{target_lang}.srt`
8. Cleans up temp files, refreshes external subs list

### Settings — AI Configuration
- `ai_provider`: "openai", "anthropic", or "" (disabled)
- `openai_api_key` / `anthropic_api_key`: stored in settings.json, never returned to frontend
- Frontend shows `_key_set` booleans, same pattern as Radarr/Sonarr keys

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
- Python: fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings, python-multipart, ffsubsync, pysubs2, openai, anthropic, langdetect
- System: ffmpeg (includes ffprobe), alass-cli (optional, for alass sync engine)

## Important Notes
- Radarr/Sonarr API v3 is used (both use same `/api/v3` pattern)
- Only movies/episodes with files (`hasFile: true`) are shown
- PGS/image-based subtitle tracks are detected and disabled for sub-to-sub sync
- The sync router accepts both file upload and file path for external subtitles
- Settings API never returns raw API keys — only a boolean `_key_set` flag
- Test connection endpoint uses stored key when frontend sends empty or `(current)` placeholder
- Translate button only appears on text-based tracks (not PGS/image-based)
- Translation requires AI provider to be configured in settings
