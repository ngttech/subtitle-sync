import asyncio
import subprocess
from pathlib import Path

from app.config import get_data_dir


def _extract_sync(video_path: str, track_index: int) -> str:
    data_dir = get_data_dir()
    video_name = Path(video_path).stem
    output_path = str(data_dir / f"{video_name}_ref_{track_index}.srt")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-map", f"0:{track_index}",
        "-c:s", "srt",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extraction failed: {result.stderr[:500]}")

    if not Path(output_path).exists():
        raise RuntimeError("Extraction produced no output file")

    return output_path


async def extract_subtitle(video_path: str, track_index: int) -> str:
    return await asyncio.to_thread(_extract_sync, video_path, track_index)
