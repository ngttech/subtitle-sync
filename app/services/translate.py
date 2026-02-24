import asyncio
import json
import os
import re
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import NamedTuple

import pysubs2
from langdetect import detect

from app.config import load_settings, get_data_dir
from app.services.extract import extract_subtitle
from app.services.logs import log_action

CHUNK_THRESHOLD = 500
CHUNK_SIZE = 500
CONTEXT_OVERLAP = 30

LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "ar": "Arabic", "hi": "Hindi", "tr": "Turkish",
    "pl": "Polish", "sv": "Swedish", "da": "Danish", "no": "Norwegian",
    "fi": "Finnish", "cs": "Czech", "ro": "Romanian", "hu": "Hungarian",
    "el": "Greek", "he": "Hebrew", "th": "Thai", "vi": "Vietnamese",
    "id": "Indonesian", "ms": "Malay", "uk": "Ukrainian", "bg": "Bulgarian",
    "hr": "Croatian", "sk": "Slovak", "sl": "Slovenian", "sr": "Serbian",
    "ca": "Catalan", "af": "Afrikaans", "sw": "Swahili", "tl": "Filipino",
}


def _lang_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code.lower(), code)


DEFAULT_SYSTEM_PROMPT = (
    "You are a professional subtitle translator. "
    "Translate the following subtitle lines from {source_lang} to {target_lang}. "
    "You MUST output every line in {target_lang}. "
    "Return EXACTLY the same number of lines, one translation per line. "
    "Do NOT add line numbers, timestamps, or any extra text. "
    "Keep markup tags like <i>, </i>, <b>, </b> intact. "
    "Preserve \\N line break markers exactly as they appear. "
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


def _build_user_message(lines: list[str], target_lang: str, offset: int = 0, context_lines: list[str] | None = None) -> str:
    numbered = "\n".join(f"{i + 1 + offset}|{line}" for i, line in enumerate(lines))

    if context_lines:
        context_block = "\n".join(f"[CONTEXT] {line}" for line in context_lines)
        return (
            f"Here is context from the previously translated lines (DO NOT translate these again):\n"
            f"{context_block}\n\n"
            f"Now translate these {len(lines)} subtitle lines into {target_lang}. "
            f"Each line is prefixed with 'NUMBER|'. "
            f"\\N within an entry represents a line break — preserve these \\N markers in your output. "
            f"Return only the translated text in {target_lang} for each line, one per line, "
            f"prefixed with the same number and pipe.\n\n{numbered}"
        )

    return (
        f"Translate these {len(lines)} subtitle lines into {target_lang}. "
        f"Each line is prefixed with 'NUMBER|'. "
        f"\\N within an entry represents a line break — preserve these \\N markers in your output. "
        f"Return only the translated text in {target_lang} for each line, one per line, "
        f"prefixed with the same number and pipe.\n\n{numbered}"
    )


def _estimate_max_tokens(num_lines: int, model: str = "") -> int:
    if model.startswith("gpt-5"):
        # Reasoning models: need headroom for reasoning + output tokens
        return min(max(num_lines * 60, 4096), 32768)
    return min(max(num_lines * 30, 1024), 16384)


class LLMResponse(NamedTuple):
    text: str
    finish_reason: str
    completion_tokens: int
    reasoning_tokens: int


async def _call_llm(provider: str, api_key: str, model: str, system_content: str, user_content: str, max_tokens: int) -> LLMResponse:
    if provider == "openai":
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=max_tokens,
        )
        # GPT-5 family (reasoning models) does not support temperature
        if model.startswith("gpt-5"):
            kwargs["reasoning_effort"] = "low"
        else:
            kwargs["temperature"] = 0.3
        resp = await client.chat.completions.create(**kwargs)
        finish_reason = resp.choices[0].finish_reason or "unknown"
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0
        reasoning_tokens = 0
        if resp.usage and hasattr(resp.usage, "completion_tokens_details") and resp.usage.completion_tokens_details:
            reasoning_tokens = getattr(resp.usage.completion_tokens_details, "reasoning_tokens", 0) or 0
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
        )
    else:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_content,
            messages=[{"role": "user", "content": user_content}],
        )
        return LLMResponse(
            text=resp.content[0].text if resp.content else "",
            finish_reason=resp.stop_reason or "unknown",
            completion_tokens=resp.usage.output_tokens if resp.usage else 0,
            reasoning_tokens=0,
        )


def _parse_numbered_response(raw: str, expected_count: int, offset: int = 0) -> list[str]:
    result: dict[int, str] = {}
    last_idx = None
    for line in raw.strip().split("\n"):
        m = re.match(r"(\d+)\|(.*)$", line.strip())
        if m:
            idx = int(m.group(1))
            result[idx] = m.group(2)
            last_idx = idx
        elif last_idx is not None and line.strip():
            result[last_idx] += "\\N" + line.strip()
    return [result.get(i + 1 + offset, "") for i in range(expected_count)]


def _sse_event(type: str, percent: int, message: str, output_path: str = "") -> str:
    data = {"type": type, "percent": percent, "message": message}
    if output_path:
        data["output_path"] = output_path
    return json.dumps(data)


def _sanitize_model_for_filename(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "", model)


async def translate_subtitle_stream(
    video_path: str,
    track_index: int,
    target_language: str,
    source_language: str = "auto",
) -> AsyncGenerator[str, None]:
    settings = load_settings()

    if not settings.ai_provider:
        yield _sse_event("error", 0, "No AI provider configured. Set one in Settings.")
        return
    if settings.ai_provider == "openai" and not settings.openai_api_key:
        yield _sse_event("error", 0, "OpenAI API key not configured.")
        return
    if settings.ai_provider == "anthropic" and not settings.anthropic_api_key:
        yield _sse_event("error", 0, "Anthropic API key not configured.")
        return

    provider = settings.ai_provider
    api_key = settings.openai_api_key if provider == "openai" else settings.anthropic_api_key
    model = settings.openai_model if provider == "openai" else settings.anthropic_model

    # 1. Extract embedded track
    yield _sse_event("progress", 5, "Extracting subtitle track...")
    try:
        temp_srt = await extract_subtitle(video_path, track_index)
    except Exception as e:
        yield _sse_event("error", 0, f"Failed to extract track: {e}")
        return

    try:
        # 2. Load with pysubs2
        yield _sse_event("progress", 15, "Loading subtitle file...")
        subs = await asyncio.to_thread(pysubs2.load, temp_srt)

        # 3. Get plain text lines
        lines = [event.plaintext.replace("\n", "\\N") for event in subs]

        # 4. Detect source language
        yield _sse_event("progress", 20, "Detecting source language...")
        src_lang = source_language
        if src_lang == "auto":
            src_lang = _detect_language(lines)

        prompt_template = settings.translation_prompt.strip() if settings.translation_prompt and settings.translation_prompt.strip() else DEFAULT_SYSTEM_PROMPT
        system_content = prompt_template.format(
            source_lang=_lang_name(src_lang),
            target_lang=_lang_name(target_language),
        )

        # 5. Translate
        video_name = Path(video_path).name
        translation_start = time.time()

        if len(lines) <= CHUNK_THRESHOLD:
            yield _sse_event("progress", 30, f"Translating {len(lines)} lines...")
            msg = _build_user_message(lines, _lang_name(target_language))
            max_tok = _estimate_max_tokens(len(lines), model)
            call_start = time.time()
            llm_resp = await _call_llm(provider, api_key, model, system_content, msg, max_tok)
            call_duration = round(time.time() - call_start, 1)
            translated = _parse_numbered_response(llm_resp.text, len(lines), offset=0)
            log_action("llm_call",
                video=video_name, provider=provider, model=model,
                target_language=target_language, source_language=src_lang,
                chunk="single", lines_in_chunk=len(lines),
                max_completion_tokens=max_tok,
                finish_reason=llm_resp.finish_reason,
                completion_tokens=llm_resp.completion_tokens,
                reasoning_tokens=llm_resp.reasoning_tokens,
                output_tokens=llm_resp.completion_tokens - llm_resp.reasoning_tokens,
                parsed_filled=sum(1 for t in translated if t),
                duration_seconds=call_duration,
            )
        else:
            translated: list[str] = []
            chunks = list(range(0, len(lines), CHUNK_SIZE))
            total_chunks = len(chunks)
            for chunk_idx, start in enumerate(chunks):
                chunk = lines[start : start + CHUNK_SIZE]
                context = translated[-CONTEXT_OVERLAP:] if translated else None

                progress = 20 + int(70 * (chunk_idx / total_chunks))
                yield _sse_event("progress", progress, f"Translating chunk {chunk_idx + 1} of {total_chunks}...")

                msg = _build_user_message(chunk, _lang_name(target_language), offset=0, context_lines=context)
                max_tok = _estimate_max_tokens(len(chunk), model)
                call_start = time.time()
                llm_resp = await _call_llm(provider, api_key, model, system_content, msg, max_tok)
                call_duration = round(time.time() - call_start, 1)
                parsed = _parse_numbered_response(llm_resp.text, len(chunk), offset=0)
                translated.extend(parsed)
                log_action("llm_call",
                    video=video_name, provider=provider, model=model,
                    target_language=target_language, source_language=src_lang,
                    chunk=f"{chunk_idx + 1}/{total_chunks}", lines_in_chunk=len(chunk),
                    max_completion_tokens=max_tok,
                    finish_reason=llm_resp.finish_reason,
                    completion_tokens=llm_resp.completion_tokens,
                    reasoning_tokens=llm_resp.reasoning_tokens,
                    output_tokens=llm_resp.completion_tokens - llm_resp.reasoning_tokens,
                    parsed_filled=sum(1 for t in parsed if t),
                    duration_seconds=call_duration,
                )

        # 6. Apply translations
        yield _sse_event("progress", 90, "Saving translated file...")
        applied = 0
        for i, event in enumerate(subs):
            if i < len(translated) and translated[i]:
                event.text = translated[i]
                applied += 1

        # 7. Save output with [ai-model] tag
        video = Path(video_path)
        model_tag = _sanitize_model_for_filename(model)
        output_path = str(video.parent / f"{video.stem}[ai-{model_tag}].{target_language}.srt")
        await asyncio.to_thread(subs.save, output_path, format_="srt")

        total_duration = round(time.time() - translation_start, 1)
        log_action("translation_complete",
            video=video_name, model=model,
            target_language=target_language, source_language=src_lang,
            total_lines=len(lines), applied_lines=applied,
            output_path=output_path, total_duration_seconds=total_duration,
        )

        yield _sse_event("complete", 100, f"Translated {len(lines)} lines ({src_lang} -> {target_language})", output_path)

    except Exception as e:
        log_action("translation_error",
            video=Path(video_path).name, model=model,
            target_language=target_language,
            error=str(e)[:500],
        )
        yield _sse_event("error", 0, f"Translation failed: {e}")
    finally:
        if os.path.exists(temp_srt):
            os.remove(temp_srt)
