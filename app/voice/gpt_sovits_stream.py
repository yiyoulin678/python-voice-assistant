from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from http.client import IncompleteRead
from typing import Any


def build_gpt_sovits_payload(
    *,
    text: str,
    text_lang: str,
    ref_audio_path: str,
    prompt_text: str,
    prompt_lang: str,
    streaming_mode: bool,
) -> dict[str, Any]:
    return {
        "text": text,
        "text_lang": text_lang,
        "ref_audio_path": ref_audio_path,
        "prompt_text": prompt_text,
        "prompt_lang": prompt_lang,
        "text_split_method": "cut0",
        "batch_size": 1,
        "media_type": "wav",
        "streaming_mode": streaming_mode,
        "top_k": 15,
        "top_p": 1,
        "temperature": 1,
        "repetition_penalty": 1.2,
    }


def parse_wav_header_sample_rate(header: bytes) -> int | None:
    if len(header) < 28:
        return None
    if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
        return None
    return int.from_bytes(header[24:28], "little")


def iter_http_body_chunks(response: Any, *, chunk_size: int = 4096) -> Iterator[bytes]:
    """尽量从 HTTP 响应体逐块读取；兼容 IncompleteRead 与提前断连。"""
    fp = getattr(response, "fp", None)
    if fp is not None:
        while True:
            try:
                if hasattr(fp, "read1"):
                    data = fp.read1(chunk_size)
                else:
                    data = fp.read(chunk_size)
            except IncompleteRead as exc:
                if exc.partial:
                    yield exc.partial
                break
            if not data:
                break
            yield data
        return

    while True:
        try:
            data = response.read(chunk_size)
        except IncompleteRead as exc:
            if exc.partial:
                yield exc.partial
            break
        if not data:
            break
        yield data


def iter_streaming_pcm_chunks(
    response: Any,
    *,
    chunk_size: int = 4096,
) -> Iterator[tuple[int, bytes]]:
    """从 GPT-SoVITS streaming_mode 响应中逐块产出 (sample_rate, pcm_bytes)。"""
    buffer = b""
    sample_rate = 32000
    header_stripped = False

    for data in iter_http_body_chunks(response, chunk_size=chunk_size):
        buffer += data

        if not header_stripped:
            if len(buffer) < 44:
                continue
            parsed_rate = parse_wav_header_sample_rate(buffer[:44])
            if parsed_rate is not None:
                sample_rate = parsed_rate
            buffer = buffer[44:]
            header_stripped = True

        if buffer:
            yield sample_rate, buffer
            buffer = b""

    if not header_stripped and buffer:
        if buffer.startswith(b"RIFF") and len(buffer) >= 44:
            parsed_rate = parse_wav_header_sample_rate(buffer[:44])
            if parsed_rate is not None:
                sample_rate = parsed_rate
            buffer = buffer[44:]
        if buffer:
            yield sample_rate, buffer


def request_gpt_sovits_interrupt(api_url: str, *, timeout_seconds: int = 3) -> bool:
    """调用 AIFE 风格 /interrupt 端点；不存在时静默返回 False。"""
    parsed_path = api_url.rstrip("/")
    if parsed_path.endswith("/tts"):
        interrupt_url = parsed_path[: -len("/tts")] + "/interrupt"
    else:
        interrupt_url = parsed_path + "/interrupt"

    request = urllib.request.Request(url=interrupt_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response.read()
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        return False
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def post_json_stream(
    api_url: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: int,
    on_http_error: Callable[[int, str], None] | None = None,
) -> Any | None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=api_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "audio/x-wav"},
    )
    try:
        return urllib.request.urlopen(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        if on_http_error is not None:
            on_http_error(exc.code, error_body)
        return None
    except urllib.error.URLError as exc:
        if on_http_error is not None:
            on_http_error(0, str(exc.reason))
        return None
    except TimeoutError:
        if on_http_error is not None:
            on_http_error(0, "timeout")
        return None
