from __future__ import annotations

import numpy as np

from app.voice.audio_io import audio_peak, audio_rms, is_silent_audio
from app.voice.speech_to_text import normalize_recording_levels


def test_is_silent_uses_peak_for_quiet_microphone() -> None:
    quiet = (np.sin(np.linspace(0, 8 * np.pi, 16000)) * 200).astype(np.int16)
    assert audio_rms(quiet) < 0.008
    assert audio_peak(quiet) > 0.006
    assert not is_silent_audio(quiet)


def test_is_silent_detects_true_silence() -> None:
    silent = np.zeros(16000, dtype=np.int16)
    assert is_silent_audio(silent)


def test_normalize_boosts_quiet_signal() -> None:
    quiet = (np.sin(np.linspace(0, 4 * np.pi, 8000)) * 300).astype(np.int16)
    boosted = normalize_recording_levels(quiet)
    assert float(np.max(np.abs(boosted))) >= 0.2
