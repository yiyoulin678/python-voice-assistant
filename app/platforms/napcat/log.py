from __future__ import annotations

from typing import Any

from app.core.debug_log import debug_log, format_debug_data
from app.platforms.napcat.event_log import napcat_event_log


def napcat_log(message: str, data: Any | None = None) -> None:
    napcat_event_log().append(message, data)
    line = f"[NapCat] {message}"
    if data is not None:
        line = f"{line} {format_debug_data(data)}"
    print(line)
    debug_log("NapCat", message, data)
