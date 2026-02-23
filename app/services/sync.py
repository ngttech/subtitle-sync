import asyncio
import re
import shutil
import subprocess
from pathlib import Path


def _find_ffsubsync_cmd() -> list[str]:
    if shutil.which("ffsubsync"):
        return ["ffsubsync"]
    return ["python", "-m", "ffsubsync"]


def _run_ffsubsync(reference_path: str, sub_path: str, output_path: str) -> tuple[bool, str, float]:
    cmd = _find_ffsubsync_cmd() + [
        reference_path,
        "-i", sub_path,
        "-o", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    output = result.stdout + "\n" + result.stderr

    offset_ms = 0.0
    offset_match = re.search(r"offset seconds:\s*([-\d.]+)", output, re.IGNORECASE)
    if offset_match:
        offset_ms = float(offset_match.group(1)) * 1000

    if result.returncode != 0:
        return False, f"ffsubsync failed: {output[:500]}", offset_ms

    if not Path(output_path).exists():
        return False, "ffsubsync produced no output file", offset_ms

    return True, "Sync completed successfully", offset_ms


def _build_output_path(video_path: str, language: str, ext: str = ".srt") -> str:
    video = Path(video_path)
    lang_suffix = f".{language}" if language else ".synced"
    output_name = f"{video.stem}{lang_suffix}{ext}"
    return str(video.parent / output_name)


async def sync_sub_to_sub(
    video_path: str,
    reference_sub_path: str,
    external_sub_path: str,
    output_language: str = "",
) -> tuple[bool, str, str, float]:
    ext = Path(external_sub_path).suffix or ".srt"
    output_path = _build_output_path(video_path, output_language, ext)
    success, message, offset_ms = await asyncio.to_thread(
        _run_ffsubsync, reference_sub_path, external_sub_path, output_path
    )
    return success, message, output_path if success else "", offset_ms


async def sync_sub_to_audio(
    video_path: str,
    external_sub_path: str,
    output_language: str = "",
) -> tuple[bool, str, str, float]:
    ext = Path(external_sub_path).suffix or ".srt"
    output_path = _build_output_path(video_path, output_language, ext)
    success, message, offset_ms = await asyncio.to_thread(
        _run_ffsubsync, video_path, external_sub_path, output_path
    )
    return success, message, output_path if success else "", offset_ms
