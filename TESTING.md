# Subtitle Sync — Testing & Setup Guide

## Prerequisites
- Python 3.10+
- ffmpeg (includes ffprobe) installed and on PATH
- ffsubsync (`pip install ffsubsync`)
- Radarr and/or Sonarr running with API access

## Quick Start

```bash
cd "Subtitle Sync"
pip install -r requirements.txt
python run.py
```

Then open: http://localhost:8765

## Testing Checklist

### 1. App Startup
- [ ] `python run.py` starts without errors
- [ ] http://localhost:8765 loads the web UI

### 2. Health Check (Dashboard)
- [ ] Dashboard shows ffmpeg, ffprobe, ffsubsync status
- [ ] All three show "Available" with green badges
- [ ] If any missing, install them before continuing

### 3. Settings Page
- [ ] Navigate to Settings (#/settings)
- [ ] Enter Radarr URL (e.g., `http://localhost:7878`) and API key
- [ ] Click "Test Connection" — should show Radarr version
- [ ] Enter Sonarr URL (e.g., `http://localhost:8989`) and API key
- [ ] Click "Test Connection" — should show Sonarr version
- [ ] Add path mappings if Docker paths differ from local paths
  - Example: From `/movies` → To `D:\Movies`
- [ ] Click "Save Settings" — should confirm saved
- [ ] Refresh page — settings should persist

### 4. Movies Page
- [ ] Navigate to Movies (#/movies)
- [ ] Should see last 20 movies from Radarr (sorted by date added)
- [ ] Search for a movie by name — results should filter
- [ ] Click a movie row — should navigate to movie detail

### 5. Movie Detail Page
- [ ] Shows movie title, year, file path
- [ ] "Embedded Subtitle Tracks" lists tracks from ffprobe
  - Each track shows: index, language, codec, default/forced flags
  - Image-based (PGS) tracks are disabled with warning
- [ ] "External Subtitle" section shows .srt/.ass files in movie folder
- [ ] "Upload File" tab allows selecting a local subtitle file

### 6. Sync Test (Movie)
- [ ] Select a reference track (embedded English subtitle)
- [ ] Select an external subtitle (or upload one)
- [ ] Set output language (e.g., "es")
- [ ] Click "Sync Subtitles"
- [ ] Should show "Syncing..." with spinner
- [ ] On success: shows offset in ms and output file path
- [ ] Verify the synced .srt file exists next to the video file

### 7. TV Shows Page
- [ ] Navigate to TV Shows (#/shows)
- [ ] Should see last 20 shows from Sonarr
- [ ] Search works
- [ ] Click a show → navigates to episodes

### 8. Episodes Page
- [ ] Shows episodes grouped by season
- [ ] Click an episode → navigates to episode detail

### 9. Episode Detail Page
- [ ] Same sync UI as movie detail
- [ ] Full sync workflow works end-to-end

### 10. Sub-to-Audio Fallback
- [ ] On a movie/episode with no text-based embedded subs
- [ ] Select "Sub-to-Audio" sync mode
- [ ] Upload/select external sub and sync
- [ ] Should work (slower than sub-to-sub)

### 11. Cache
- [ ] After first load, movies/shows load instantly (cached)
- [ ] Settings → "Refresh Library Cache" clears cache
- [ ] Next page load fetches fresh data from Radarr/Sonarr

### 12. Docker (optional)
- [ ] Edit `docker-compose.yml` to set correct media volume paths
- [ ] `docker compose up --build` starts container
- [ ] http://localhost:8765 loads
- [ ] Health check shows all tools available
- [ ] Full sync workflow works inside container

## Common Issues

| Issue | Fix |
|-------|-----|
| ffsubsync not found | `pip install ffsubsync` or ensure it's on PATH |
| ffmpeg not found | Install from https://ffmpeg.org/download.html |
| Radarr/Sonarr connection fails | Check URL and API key; ensure services are running |
| File not found during sync | Check path mappings in Settings; ensure media paths are accessible |
| PGS-only tracks | Use "Sub-to-Audio" mode instead of "Sub-to-Sub" |
| Sync takes too long | Sub-to-audio is slower (~1min per hour of video); sub-to-sub is fast |

## File Structure

```
subtitle-sync/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings management
│   ├── services/            # Business logic (radarr, sonarr, ffprobe, sync)
│   ├── routers/             # API endpoints
│   ├── models/              # Pydantic models
│   └── static/              # Frontend (HTML/JS/CSS)
├── config/settings.json     # Created at runtime
├── data/                    # Temp files (auto-cleaned)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run.py                   # Entry point
```
