import asyncio
import re
import shutil
import subprocess
from pathlib import Path


def _find_ffsubsync_cmd() -> list[str]:
    if shutil.which("ffsubsync"):
        return ["ffsubsync"]
    return ["python", "-m", "ffsubsync"]


def _find_alass_cmd() -> list[str]:
    if shutil.which("alass-cli"):
        return ["alass-cli"]
    if shutil.which("alass"):
        return ["alass"]
    raise RuntimeError("alass-cli not found. Install alass or use ffsubsync.")


def _run_ffsubsync(reference_path: str, sub_path: str, output_path: str) -> tuple[bool, str, float]:
    cmd = _find_ffsubsync_cmd() + [
        reference_path,
        "-i", sub_path,
        "-o", output_path,
        "--gss",
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


def _run_alass(reference_path: str, sub_path: str, output_path: str) -> tuple[bool, str, float]:
    cmd = _find_alass_cmd() + [reference_path, sub_path, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    output = result.stdout + "\n" + result.stderr

    offset_ms = 0.0
    # alass outputs "shifted subtitle by X ms" or similar
    offset_match = re.search(r"by\s+([-\d.]+)\s*ms", output, re.IGNORECASE)
    if offset_match:
        offset_ms = float(offset_match.group(1))

    if result.returncode != 0:
        return False, f"alass failed: {output[:500]}", offset_ms

    if not Path(output_path).exists():
        return False, "alass produced no output file", offset_ms

    return True, "Sync completed successfully (alass)", offset_ms


def _build_output_path(video_path: str, language: str, ext: str = ".srt", tag: str = "") -> str:
    video = Path(video_path)
    tag_part = f"[{tag}]" if tag else ""
    lang_suffix = f".{language}" if language else ".synced"
    output_name = f"{video.stem}{tag_part}{lang_suffix}{ext}"
    return str(video.parent / output_name)


def _get_runner(sync_engine: str):
    if sync_engine == "alass":
        return _run_alass
    return _run_ffsubsync


async def sync_sub_to_sub(
    video_path: str,
    reference_sub_path: str,
    external_sub_path: str,
    output_language: str = "",
    sync_engine: str = "ffsubsync",
) -> tuple[bool, str, str, float]:
    ext = Path(external_sub_path).suffix or ".srt"
    output_path = _build_output_path(video_path, output_language, ext, tag=f"synced-{sync_engine}")
    runner = _get_runner(sync_engine)
    success, message, offset_ms = await asyncio.to_thread(
        runner, reference_sub_path, external_sub_path, output_path
    )
    return success, message, output_path if success else "", offset_ms


async def sync_sub_to_audio(
    video_path: str,
    external_sub_path: str,
    output_language: str = "",
    sync_engine: str = "ffsubsync",
) -> tuple[bool, str, str, float]:
    ext = Path(external_sub_path).suffix or ".srt"
    output_path = _build_output_path(video_path, output_language, ext, tag=f"synced-{sync_engine}")
    runner = _get_runner(sync_engine)
    success, message, offset_ms = await asyncio.to_thread(
        runner, video_path, external_sub_path, output_path
    )
    return success, message, output_path if success else "", offset_ms
