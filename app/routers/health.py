import shutil
import subprocess

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _check_tool(name: str) -> dict:
    path = shutil.which(name)
    if not path:
        return {"available": False, "version": None, "path": None}
    try:
        result = subprocess.run(
            [name, "-version"], capture_output=True, text=True, timeout=10
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else None
        return {"available": True, "version": version_line, "path": path}
    except Exception:
        return {"available": True, "version": None, "path": path}


def _check_ffsubsync() -> dict:
    path = shutil.which("ffsubsync")
    if not path:
        try:
            result = subprocess.run(
                ["python", "-m", "ffsubsync", "--help"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return {"available": True, "version": "python -m ffsubsync", "path": "python -m ffsubsync"}
        except Exception:
            pass
        return {"available": False, "version": None, "path": None}
    try:
        result = subprocess.run(
            [path, "--help"], capture_output=True, text=True, timeout=10
        )
        return {"available": True, "version": "ffsubsync", "path": path}
    except Exception:
        return {"available": True, "version": None, "path": path}


@router.get("/health")
async def health_check():
    ffmpeg = _check_tool("ffmpeg")
    ffprobe = _check_tool("ffprobe")
    ffsubsync = _check_ffsubsync()

    all_ok = ffmpeg["available"] and ffprobe["available"] and ffsubsync["available"]

    return {
        "status": "ok" if all_ok else "degraded",
        "tools": {
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
            "ffsubsync": ffsubsync,
        },
    }
