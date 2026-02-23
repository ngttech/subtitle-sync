from pathlib import Path

from app.models.subtitle import ExternalSubtitle

SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}


def scan_external_subs(folder_path: str) -> list[ExternalSubtitle]:
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []

    subs: list[ExternalSubtitle] = []
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in SUBTITLE_EXTENSIONS:
            language = _guess_language(f.stem)
            subs.append(ExternalSubtitle(
                filename=f.name,
                path=str(f),
                language=language,
            ))
    return subs


def _guess_language(stem: str) -> str:
    parts = stem.rsplit(".", 1)
    if len(parts) == 2:
        lang = parts[1].lower()
        if len(lang) in (2, 3) and lang.isalpha():
            return lang
    return ""
