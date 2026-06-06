from __future__ import annotations

import numpy as np

from app.voice.stt_settings import STTSettings, VOICE_CALL_SILENCE_SECONDS
from app.voice.voice_call_listener import (
    VoiceCallConfig,
    is_speech_block,
    should_finalize_utterance,
)


def test_is_speech_block_detects_loud_audio() -> None:
    loud = (np.ones(1600, dtype=np.float32) * 0.2).astype(np.int16)
    assert is_speech_block(loud, rms_threshold=0.006, peak_threshold=0.01)


def test_is_speech_block_rejects_silence() -> None:
    quiet = np.zeros(1600, dtype=np.int16)
    assert not is_speech_block(quiet, rms_threshold=0.006, peak_threshold=0.01)


def test_should_finalize_after_silence_window() -> None:
    config = VoiceCallConfig.from_stt_settings(
        STTSettings(voice_call_silence_seconds=VOICE_CALL_SILENCE_SECONDS)
    )
    assert should_finalize_utterance(
        speech_seconds=1.0,
        silence_seconds=config.silence_seconds,
        config=config,
    )
    assert not should_finalize_utterance(
        speech_seconds=0.2,
        silence_seconds=config.silence_seconds,
        config=config,
    )
