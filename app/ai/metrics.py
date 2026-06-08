from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class AiMetricsRecorder:
    """记录 AI 运行事件，供课设统计图与队友后台消费。"""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.events_path = self.base_dir / "data" / "metrics" / "ai_events.jsonl"
        self._lock = threading.Lock()
        self._logger = logging.getLogger("sakura.ai")
        if not self._logger.handlers:
            self._configure_logger()

    def record(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        event = {
            "event_type": event_type,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "payload": payload or {},
        }
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
        self._logger.info("%s %s", event_type, json.dumps(payload or {}, ensure_ascii=False))

    def _configure_logger(self) -> None:
        log_dir = self.base_dir / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "ai.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
