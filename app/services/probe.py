import asyncio
import json
import subprocess

from app.models.subtitle import SubtitleTrack

IMAGE_CODECS = {"hdmv_pgs_subtitle", "dvd_subtitle", "dvdsub", "pgssub", "pgs"}


def _probe_sync(video_path: str) -> list[SubtitleTrack]:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "s",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:500]}")

    data = json.loads(result.stdout)
    tracks: list[SubtitleTrack] = []

    for stream in data.get("streams", []):
        codec = stream.get("codec_name", "unknown")
        tags = stream.get("tags", {})
        disposition = stream.get("disposition", {})

        tracks.append(SubtitleTrack(
            index=stream.get("index", 0),
            codec=codec,
            language=tags.get("language", ""),
            title=tags.get("title", ""),
            default=bool(disposition.get("default", 0)),
            forced=bool(disposition.get("forced", 0)),
            text_based=codec.lower() not in IMAGE_CODECS,
        ))

    return tracks


async def probe_subtitles(video_path: str) -> list[SubtitleTrack]:
    return await asyncio.to_thread(_probe_sync, video_path)
