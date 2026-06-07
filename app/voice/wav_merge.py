from __future__ import annotations

import uuid
import wave
from pathlib import Path


def merge_wav_files(source_paths: list[Path], destination: Path) -> Path:
    if not source_paths:
        raise ValueError("没有可合并的音频文件")
    if len(source_paths) == 1:
        return source_paths[0]

    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source_paths[0]), "rb") as first_wave:
        sample_width = first_wave.getsampwidth()
        frame_rate = first_wave.getframerate()
        channels = first_wave.getnchannels()
        parameters = first_wave.getparams()

    with wave.open(str(destination), "wb") as output:
        output.setparams(parameters)
        for index, source_path in enumerate(source_paths):
            with wave.open(str(source_path), "rb") as input_wave:
                if (
                    input_wave.getsampwidth() != sample_width
                    or input_wave.getframerate() != frame_rate
                    or input_wave.getnchannels() != channels
                ):
                    raise ValueError(f"音频参数不一致，无法合并：{source_path}")
                output.writeframes(input_wave.readframes(input_wave.getnframes()))
    return destination


def build_chunk_merge_path(base_dir: Path, prefix: str = "tts-merged") -> Path:
    temp_dir = base_dir / "temp" / "tts_chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / f"{prefix}-{uuid.uuid4().hex}.wav"
