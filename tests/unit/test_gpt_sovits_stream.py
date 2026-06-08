from __future__ import annotations

import io

from http.client import IncompleteRead

from app.voice.gpt_sovits_stream import (
    build_gpt_sovits_payload,
    iter_http_body_chunks,
    iter_streaming_pcm_chunks,
    parse_wav_header_sample_rate,
)


def _make_wav_header(sample_rate: int = 32000) -> bytes:
    import struct
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x01" * 8)
    return buffer.getvalue()


def test_build_gpt_sovits_payload_enables_streaming_mode() -> None:
    payload = build_gpt_sovits_payload(
        text="こんにちは",
        text_lang="ja",
        ref_audio_path="ref.wav",
        prompt_text="参考",
        prompt_lang="ja",
        streaming_mode=True,
    )
    assert payload["streaming_mode"] is True
    assert payload["text_split_method"] == "cut0"


def test_parse_wav_header_sample_rate() -> None:
    header = _make_wav_header(24000)
    assert parse_wav_header_sample_rate(header[:44]) == 24000


def test_iter_http_body_chunks_handles_incomplete_read() -> None:
    header = _make_wav_header(32000)[:44]
    pcm = b"\xab\xcd" * 8

    class BrokenReader:
        def __init__(self) -> None:
            self._payload = header + pcm
            self._pos = 0

        def read1(self, size: int) -> bytes:
            if self._pos == 0:
                self._pos = len(header)
                raise IncompleteRead(header, len(header) + len(pcm))
            return b""

    class FakeResponse:
        fp = None

        def __init__(self) -> None:
            self.fp = BrokenReader()

    chunks = list(iter_http_body_chunks(FakeResponse(), chunk_size=64))
    assert header in b"".join(chunks)


def test_iter_streaming_pcm_chunks_strips_header() -> None:
    header = _make_wav_header(32000)[:44]
    pcm = b"\x12\x34" * 16
    stream = io.BytesIO(header + pcm)

    chunks = list(iter_streaming_pcm_chunks(stream, chunk_size=32))
    merged = b"".join(chunk for _, chunk in chunks)
    sample_rate = chunks[0][0]
    assert sample_rate == 32000
    assert merged == pcm
