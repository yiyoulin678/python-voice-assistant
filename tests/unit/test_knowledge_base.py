from __future__ import annotations

from pathlib import Path

from app.rag.knowledge_base import KnowledgeBase


def test_knowledge_base_keyword_search(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "data" / "knowledge"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "demo.md").write_text(
        "Python 课设需要 GUI、权限、网络、数据库和 AI 核心模块。\n\n"
        "进阶功能可以选择 Matplotlib 可视化与 logging 日志。",
        encoding="utf-8",
    )
    base = KnowledgeBase(tmp_path)
    assert base.reload() >= 1

    hits = base.search("数据库 CRUD", limit=3)
    assert hits
    assert any("数据库" in hit.text for hit in hits)

    context = base.format_context("课设基础必做有哪些")
    assert "知识库检索结果" in context
    assert "GUI" in context or "权限" in context
