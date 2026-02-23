import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.config import get_data_dir
from app.models.subtitle import SyncResponse
from app.services.extract import extract_subtitle
from app.services.sync import sync_sub_to_sub, sync_sub_to_audio

router = APIRouter(tags=["sync"])


@router.post("/sync", response_model=SyncResponse)
async def run_sync(
    video_path: str = Form(...),
    reference_track_index: int | None = Form(default=None),
    external_sub_path: str | None = Form(default=None),
    sync_mode: str = Form(default="sub-to-sub"),
    output_language: str = Form(default=""),
    uploaded_sub: UploadFile | None = File(default=None),
):
    if not Path(video_path).exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {video_path}")

    # Resolve the external subtitle: either uploaded file or existing path
    sub_path = external_sub_path
    temp_upload_path: str | None = None

    if uploaded_sub and uploaded_sub.filename:
        data_dir = get_data_dir()
        temp_upload_path = str(data_dir / uploaded_sub.filename)
        content = await uploaded_sub.read()
        Path(temp_upload_path).write_bytes(content)
        sub_path = temp_upload_path

    if not sub_path:
        raise HTTPException(status_code=400, detail="No external subtitle provided (upload or path)")

    if not Path(sub_path).exists():
        raise HTTPException(status_code=400, detail=f"Subtitle file not found: {sub_path}")

    ref_temp_path: str | None = None

    try:
        if sync_mode == "sub-to-sub":
            if reference_track_index is None:
                raise HTTPException(
                    status_code=400,
                    detail="reference_track_index required for sub-to-sub mode",
                )
            # Extract the reference subtitle track
            ref_temp_path = await extract_subtitle(video_path, reference_track_index)
            success, message, output_path, offset_ms = await sync_sub_to_sub(
                video_path, ref_temp_path, sub_path, output_language,
            )
        elif sync_mode == "sub-to-audio":
            success, message, output_path, offset_ms = await sync_sub_to_audio(
                video_path, sub_path, output_language,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown sync mode: {sync_mode}")

        return SyncResponse(
            success=success,
            message=message,
            output_path=output_path,
            offset_ms=offset_ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        return SyncResponse(success=False, message=str(e)[:500])
    finally:
        # Clean up temp files
        if ref_temp_path and os.path.exists(ref_temp_path):
            os.remove(ref_temp_path)
        if temp_upload_path and os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)
