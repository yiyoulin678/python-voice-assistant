from __future__ import annotations

from pathlib import Path


class UserSession:
    user_id: int | None = None
    username: str = ""
    role: str = "user"


def user_database_path(base_dir: Path) -> Path:
    return base_dir / "users.db"


def role_display_name(role: str) -> str:
    if role.lower() == "admin":
        return "管理员"
    return "普通用户"