from pydantic import BaseModel


class SubtitleTrack(BaseModel):
    index: int
    codec: str
    language: str = ""
    title: str = ""
    default: bool = False
    forced: bool = False
    text_based: bool = True


class ExternalSubtitle(BaseModel):
    filename: str
    path: str
    language: str = ""


class SyncRequest(BaseModel):
    video_path: str
    reference_track_index: int | None = None
    external_sub_path: str | None = None
    sync_mode: str = "sub-to-sub"  # "sub-to-sub" or "sub-to-audio"
    output_language: str = ""


class SyncResponse(BaseModel):
    success: bool
    message: str
    output_path: str = ""
    offset_ms: float = 0
