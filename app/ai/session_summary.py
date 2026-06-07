from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.llm.api_client import ChatMessage, OpenAICompatibleClient

SUMMARY_SYSTEM_PROMPT = """你是会话纪要助手。根据用户提供的一轮「用户与桌宠助手」对话，写一段简短中文纪要。

要求：
- 用 3～6 条要点，每条一行，以「- 」开头
- 只总结对话里真正出现的信息，不要编造
- 可包含：用户问题、助手结论、待办、情绪氛围（若明显）
- 不要 JSON，不要 Markdown 标题，不要客套开场白"""


@dataclass(frozen=True)
class SessionTurn:
    user_text: str
    assistant_text: str


def session_summary_note_path(notes_dir: Path, character_id: str) -> Path:
    safe_id = character_id.strip() or "default"
    return notes_dir / f"{safe_id}-纪要.txt"


def should_summarize_turn(turn: SessionTurn, *, min_user_chars: int = 2, min_assistant_chars: int = 8) -> bool:
    user_text = turn.user_text.strip()
    assistant_text = turn.assistant_text.strip()
    return len(user_text) >= min_user_chars and len(assistant_text) >= min_assistant_chars


def build_summary_messages(turn: SessionTurn) -> list[ChatMessage]:
    return [
        {
            "role": "user",
            "content": (
                f"用户：{turn.user_text.strip()}\n\n"
                f"助手：{turn.assistant_text.strip()}"
            ),
        }
    ]


def generate_session_summary(api_client: OpenAICompatibleClient, turn: SessionTurn) -> str:
    content = api_client.complete_raw(
        SUMMARY_SYSTEM_PROMPT,
        build_summary_messages(turn),
        temperature=0.3,
    )
    summary = content.strip()
    if not summary:
        raise ValueError("纪要生成为空")
    return summary


def append_session_summary(note_path: Path, summary: str, *, timestamp: str | None = None) -> None:
    note_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n\n## [{stamp}]\n{summary.strip()}\n"
    with note_path.open("a", encoding="utf-8") as handle:
        handle.write(block)
