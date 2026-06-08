from __future__ import annotations

import json
from pathlib import Path

from app.ui.live2d_motions import load_motion_catalog


def test_load_motion_catalog_reads_named_groups(tmp_path: Path) -> None:
    model_json = tmp_path / "Mao.model3.json"
    model_json.write_text(
        json.dumps(
            {
                "Version": 3,
                "FileReferences": {
                    "Motions": {
                        "Idle": [{"Name": "待机", "File": "motions/mtn_01.motion3.json"}],
                        "TapBody": [
                            {"Name": "有点小生气而上下摆手", "File": "motions/mtn_02.motion3.json"},
                            {"Name": "有点不好意思而摇晃身体", "File": "motions/mtn_03.motion3.json"},
                        ],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    catalog = load_motion_catalog(model_json)

    assert catalog["有点不好意思而摇晃身体"].group == "TapBody"
    assert catalog["有点不好意思而摇晃身体"].index == 1
    assert catalog["待机"].group == "Idle"
    assert catalog["待机"].index == 0
