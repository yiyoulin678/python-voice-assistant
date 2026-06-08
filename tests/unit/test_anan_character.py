from __future__ import annotations

from pathlib import Path

from app.config.character_loader import CharacterRegistry
from app.ui.live2d_motions import load_motion_catalog


def test_anan_1_live2d_motion_config() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    profile = CharacterRegistry(base_dir).get("anan_1")
    live2d = profile.live2d
    assert live2d is not None

    catalog = load_motion_catalog(live2d.model_json_path)
    assert "害羞摇晃" in catalog
    assert catalog["害羞摇晃"].group == "TapBody"
    assert live2d.tap_motions == ("害羞摇晃", "轻轻点头", "有点不开心")
    assert live2d.tone_motions["害羞"] == "害羞摇晃"
    assert live2d.idle_variation_motions == ("害羞摇晃", "轻轻点头")
    assert live2d.mouse_tracking_body_factor == 0.42
