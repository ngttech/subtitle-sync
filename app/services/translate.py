import asyncio
import os
import re
from pathlib import Path

import pysubs2
from langdetect import detect

from app.config import load_settings, get_data_dir
from app.services.extract import extract_subtitle

# Send whole file if ≤500 lines, otherwise chunk at 500 with context overlap
CHUNK_THRESHOLD = 500
CHUNK_SIZE = 500
CONTEXT_OVERLAP = 30  # lines from previous chunk included as context (not re-translated)

SYSTEM_PROMPT = (
    "You are a professional subtitle translator. "
    "Translate the following subtitle lines from {source_lang} to {target_lang}. "
    "Return EXACTLY the same number of lines, one translation per line. "
    "Do NOT add line numbers, timestamps, or any extra text. "
    "Keep markup tags like <i>, </i>, <b>, </b> intact. "
    "Preserve empty lines as empty lines."
)


def _detect_language(lines: list[str]) -> str:
    sample = " ".join(line for line in lines[:100] if line.strip())
    if not sample:
        return "unknown"
    try:
        return detect(sample)
    except Exception:
        return "unknown"


def _build_user_message(lines: list[str], offset: int = 0, context_lines: list[str] | None = None) -> str:
    """Build the numbered user message for the LLM.

    If context_lines is provided, they are prepended as already-translated context
    so the LLM can maintain narrative consistency, but only the numbered lines
    after the context should be translated.
    """
    numbered = "\n".join(f"{i + 1 + offset}|{line}" for i, line in enumerate(lines))

    if context_lines:
        context_block = "\n".join(f"[CONTEXT] {line}" for line in context_lines)
        return (
            f"Here is context from the previously translated lines (DO NOT translate these again):\n"
            f"{context_block}\n\n"
            f"Now translate these {len(lines)} subtitle lines. "
            f"Each line is prefixed with 'NUMBER|'. "
            f"Return only the translated text for each line, one per line, "
            f"prefixed with the same number and pipe.\n\n{numbered}"
        )

    return (
        f"Translate these {len(lines)} subtitle lines. "
        f"Each line is prefixed with 'NUMBER|'. "
        f"Return only the translated text for each line, one per line, "
        f"prefixed with the same number and pipe.\n\n{numbered}"
    )


def _estimate_max_tokens(num_lines: int) -> int:
    """Estimate max_tokens needed for the response. ~30 tokens per subtitle line is generous."""
    return min(max(num_lines * 30, 1024), 16384)


async def _translate_with_openai(
    lines: list[str], source_lang: str, target_lang: str, api_key: str
) -> list[str]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    system_content = SYSTEM_PROMPT.format(source_lang=source_lang, target_lang=target_lang)

    if len(lines) <= CHUNK_THRESHOLD:
        # Send the whole file at once
        msg = _build_user_message(lines)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": msg},
            ],
            max_tokens=_estimate_max_tokens(len(lines)),
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        return _parse_numbered_response(raw, len(lines), offset=0)

    # Chunked fallback for long subtitles
    translated: list[str] = []
    for start in range(0, len(lines), CHUNK_SIZE):
        chunk = lines[start : start + CHUNK_SIZE]

        # Include tail of previous translation as context
        context = translated[-CONTEXT_OVERLAP:] if translated else None

        msg = _build_user_message(chunk, offset=start, context_lines=context)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": msg},
            ],
            max_tokens=_estimate_max_tokens(len(chunk)),
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        parsed = _parse_numbered_response(raw, len(chunk), offset=start)
        translated.extend(parsed)

    return translated


async def _translate_with_anthropic(
    lines: list[str], source_lang: str, target_lang: str, api_key: str
) -> list[str]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    system_content = SYSTEM_PROMPT.format(source_lang=source_lang, target_lang=target_lang)

    if len(lines) <= CHUNK_THRESHOLD:
        # Send the whole file at once
        msg = _build_user_message(lines)
        resp = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=_estimate_max_tokens(len(lines)),
            system=system_content,
            messages=[{"role": "user", "content": msg}],
        )
        raw = resp.content[0].text if resp.content else ""
        return _parse_numbered_response(raw, len(lines), offset=0)

    # Chunked fallback for long subtitles
    translated: list[str] = []
    for start in range(0, len(lines), CHUNK_SIZE):
        chunk = lines[start : start + CHUNK_SIZE]

        # Include tail of previous translation as context
        context = translated[-CONTEXT_OVERLAP:] if translated else None

        msg = _build_user_message(chunk, offset=start, context_lines=context)
        resp = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=_estimate_max_tokens(len(chunk)),
            system=system_content,
            messages=[{"role": "user", "content": msg}],
        )
        raw = resp.content[0].text if resp.content else ""
        parsed = _parse_numbered_response(raw, len(chunk), offset=start)
        translated.extend(parsed)

    return translated


def _parse_numbered_response(raw: str, expected_count: int, offset: int = 0) -> list[str]:
    """Parse numbered response lines like '1|translated text'."""
    result: dict[int, str] = {}
    for line in raw.strip().split("\n"):
        m = re.match(r"(\d+)\|(.*)$", line.strip())
        if m:
            idx = int(m.group(1))
            result[idx] = m.group(2)

    # Build ordered list using the expected numbering (offset+1 .. offset+count)
    return [result.get(i + 1 + offset, "") for i in range(expected_count)]


async def translate_subtitle(
    video_path: str,
    track_index: int,
    target_language: str,
    source_language: str = "auto",
) -> tuple[bool, str, str]:
    """Extract an embedded track, translate it with AI, save next to the video.

    Returns (success, message, output_path).
    """
    settings = load_settings()

    if not settings.ai_provider:
        return False, "No AI provider configured. Set one in Settings.", ""
    if settings.ai_provider == "openai" and not settings.openai_api_key:
        return False, "OpenAI API key not configured.", ""
    if settings.ai_provider == "anthropic" and not settings.anthropic_api_key:
        return False, "Anthropic API key not configured.", ""

    # 1. Extract embedded track
    try:
        temp_srt = await extract_subtitle(video_path, track_index)
    except Exception as e:
        return False, f"Failed to extract track: {e}", ""

    try:
        # 2. Load with pysubs2
        subs = await asyncio.to_thread(pysubs2.load, temp_srt)

        # 3. Get plain text lines
        lines = [event.plaintext for event in subs]

        # 4. Detect source language
        src_lang = source_language
        if src_lang == "auto":
            src_lang = _detect_language(lines)

        # 5. Translate (whole file or chunked for long subs)
        if settings.ai_provider == "openai":
            translated = await _translate_with_openai(
                lines, src_lang, target_language, settings.openai_api_key
            )
        else:
            translated = await _translate_with_anthropic(
                lines, src_lang, target_language, settings.anthropic_api_key
            )

        # 6. Apply translations back to subtitle events
        for i, event in enumerate(subs):
            if i < len(translated) and translated[i]:
                event.text = translated[i]

        # 7. Save output
        video = Path(video_path)
        output_path = str(video.parent / f"{video.stem}.{target_language}.srt")
        await asyncio.to_thread(subs.save, output_path, format_="srt")

        return True, f"Translated {len(lines)} lines ({src_lang} -> {target_language})", output_path

    except Exception as e:
        return False, f"Translation failed: {e}", ""
    finally:
        # Clean up temp extracted file
        if os.path.exists(temp_srt):
            os.remove(temp_srt)
