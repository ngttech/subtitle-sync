from pathlib import Path

from fastapi import APIRouter, Form, HTTPException

from app.models.subtitle import TranslateResponse
from app.services.translate import translate_subtitle

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
async def translate_track(
    video_path: str = Form(...),
    track_index: int = Form(...),
    target_language: str = Form(...),
    source_language: str = Form(default="auto"),
):
    if not Path(video_path).exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")

    try:
        success, message, output_path = await translate_subtitle(
            video_path, track_index, target_language, source_language,
        )
        return TranslateResponse(success=success, message=message, output_path=output_path)
    except Exception as e:
        return TranslateResponse(success=False, message=str(e)[:500])
