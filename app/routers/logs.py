from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.logs import read_logs, clear_logs, get_log_path

router = APIRouter(tags=["logs"])


@router.get("/logs")
async def get_logs():
    return {"entries": read_logs()}


@router.get("/logs/download")
async def download_logs():
    path = get_log_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="No log file found")
    return FileResponse(
        path=str(path),
        media_type="application/x-ndjson",
        filename="subtitle_sync.log",
    )


@router.post("/logs/clear")
async def clear_logs_endpoint():
    clear_logs()
    return {"message": "Logs cleared"}
