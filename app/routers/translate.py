from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import StreamingResponse

from app.services.translate import translate_subtitle_stream

router = APIRouter(tags=["translate"])


@router.post("/translate")
async def translate_track(
    video_path: str = Form(...),
    track_index: int = Form(...),
    target_language: str = Form(...),
    source_language: str = Form(default="auto"),
):
    if not Path(video_path).exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")

    async def event_stream():
        async for event_json in translate_subtitle_stream(
            video_path, track_index, target_language, source_language,
        ):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
