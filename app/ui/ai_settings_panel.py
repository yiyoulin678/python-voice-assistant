from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ai.stats import format_event_brief, format_event_time, load_ai_events, summarize_ai_events
from app.rag.knowledge_base import KnowledgeBase


class AiSettingsPanel(QWidget):
    """设置页中的 AI 知识库与运行指标可视化。"""

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir.resolve()
        self.knowledge_base = KnowledgeBase(self.base_dir)
        self.events_path = self.base_dir / "data" / "metrics" / "ai_events.jsonl"
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        hint = QLabel(
            "查看本地文档知识库索引与 AI 运行指标。知识库文件放在 data/knowledge/；"
            "指标来自 data/metrics/ai_events.jsonl，可供课设统计图读取。",
            self,
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self._build_knowledge_group())
        layout.addWidget(self._build_metrics_group())
        layout.addStretch(1)

    def _build_knowledge_group(self) -> QGroupBox:
        group = QGroupBox("文档知识库 RAG", self)
        group_layout = QVBoxLayout(group)

        self.knowledge_status_label = QLabel("正在加载...", group)
        group_layout.addWidget(self.knowledge_status_label)

        self.knowledge_sources_table = QTableWidget(0, 2, group)
        self.knowledge_sources_table.setHorizontalHeaderLabels(["文档", "片段数"])
        self.knowledge_sources_table.verticalHeader().setVisible(False)
        self.knowledge_sources_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.knowledge_sources_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.knowledge_sources_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        group_layout.addWidget(self.knowledge_sources_table)

        search_layout = QHBoxLayout()
        self.knowledge_search_edit = QLineEdit(group)
        self.knowledge_search_edit.setPlaceholderText("试检索：课设基础必做有哪些？")
        self.knowledge_search_button = QPushButton("检索", group)
        self.knowledge_search_button.clicked.connect(self._run_knowledge_search)
        self.knowledge_reload_button = QPushButton("重建索引", group)
        self.knowledge_reload_button.clicked.connect(self.refresh_knowledge)
        search_layout.addWidget(self.knowledge_search_edit, 1)
        search_layout.addWidget(self.knowledge_search_button)
        search_layout.addWidget(self.knowledge_reload_button)
        group_layout.addLayout(search_layout)

        self.knowledge_results_table = QTableWidget(0, 3, group)
        self.knowledge_results_table.setHorizontalHeaderLabels(["来源", "相关度", "摘要"])
        self.knowledge_results_table.verticalHeader().setVisible(False)
        self.knowledge_results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.knowledge_results_table.setWordWrap(True)
        results_header = self.knowledge_results_table.horizontalHeader()
        results_header.setStretchLastSection(True)
        results_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        results_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        group_layout.addWidget(self.knowledge_results_table)
        return group

    def _build_metrics_group(self) -> QGroupBox:
        group = QGroupBox("AI 运行指标", self)
        group_layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        self.metrics_refresh_button = QPushButton("刷新指标", group)
        self.metrics_refresh_button.clicked.connect(self.refresh_metrics)
        toolbar.addWidget(self.metrics_refresh_button)
        toolbar.addStretch(1)
        group_layout.addLayout(toolbar)

        summary_box = QGroupBox("汇总", group)
        summary_form = QFormLayout(summary_box)
        self.metric_total_label = QLabel("0", summary_box)
        self.metric_chat_label = QLabel("0", summary_box)
        self.metric_retry_label = QLabel("0", summary_box)
        self.metric_latency_label = QLabel("0 ms", summary_box)
        self.metric_rag_label = QLabel("0", summary_box)
        self.metric_tones_label = QLabel("暂无", summary_box)
        self.metric_tools_label = QLabel("暂无", summary_box)
        summary_form.addRow("事件总数", self.metric_total_label)
        summary_form.addRow("完成对话", self.metric_chat_label)
        summary_form.addRow("输出校验重试", self.metric_retry_label)
        summary_form.addRow("平均耗时", self.metric_latency_label)
        summary_form.addRow("命中知识库", self.metric_rag_label)
        summary_form.addRow("语气分布", self.metric_tones_label)
        summary_form.addRow("工具调用", self.metric_tools_label)
        group_layout.addWidget(summary_box)

        self.metrics_events_table = QTableWidget(0, 3, group)
        self.metrics_events_table.setHorizontalHeaderLabels(["时间", "类型", "摘要"])
        self.metrics_events_table.verticalHeader().setVisible(False)
        self.metrics_events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.metrics_events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        events_header = self.metrics_events_table.horizontalHeader()
        events_header.setStretchLastSection(True)
        events_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        events_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        group_layout.addWidget(self.metrics_events_table)
        return group

    def refresh_all(self) -> None:
        self.refresh_knowledge()
        self.refresh_metrics()

    def refresh_knowledge(self) -> None:
        try:
            chunk_count = self.knowledge_base.reload(force=True)
            sources = self.knowledge_base.list_sources()
        except Exception as exc:  # noqa: BLE001
            self.knowledge_status_label.setText(f"知识库加载失败：{exc}")
            return

        knowledge_dir = self.base_dir / "data" / "knowledge"
        self.knowledge_status_label.setText(
            f"已索引 {chunk_count} 个片段，{len(sources)} 个文档。"
            f" 目录：{knowledge_dir}"
        )

        counts = self.knowledge_base.source_chunk_counts()

        self.knowledge_sources_table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            self.knowledge_sources_table.setItem(row, 0, QTableWidgetItem(source))
            count_item = QTableWidgetItem(str(counts.get(source, 0)))
            count_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.knowledge_sources_table.setItem(row, 1, count_item)

        if not self.knowledge_search_edit.text().strip():
            self.knowledge_results_table.setRowCount(0)

    def _run_knowledge_search(self) -> None:
        query = self.knowledge_search_edit.text().strip()
        if not query:
            self.knowledge_results_table.setRowCount(0)
            return
        try:
            hits = self.knowledge_base.search(query, limit=8)
        except Exception as exc:  # noqa: BLE001
            self.knowledge_results_table.setRowCount(1)
            self.knowledge_results_table.setItem(0, 0, QTableWidgetItem("错误"))
            self.knowledge_results_table.setItem(0, 1, QTableWidgetItem(""))
            self.knowledge_results_table.setItem(0, 2, QTableWidgetItem(str(exc)))
            return

        self.knowledge_results_table.setRowCount(len(hits))
        for row, hit in enumerate(hits):
            self.knowledge_results_table.setItem(row, 0, QTableWidgetItem(hit.source))
            score_item = QTableWidgetItem(f"{hit.score:.2f}")
            score_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.knowledge_results_table.setItem(row, 1, score_item)
            preview = hit.text.replace("\n", " ")
            if len(preview) > 160:
                preview = preview[:159] + "…"
            self.knowledge_results_table.setItem(row, 2, QTableWidgetItem(preview))
        self.knowledge_results_table.resizeRowsToContents()

    def refresh_metrics(self) -> None:
        events = load_ai_events(self.events_path, limit=300)
        summary = summarize_ai_events(events)

        self.metric_total_label.setText(str(summary.total_events))
        self.metric_chat_label.setText(str(summary.chat_completed))
        self.metric_retry_label.setText(str(summary.reply_parse_retry))
        self.metric_latency_label.setText(
            f"{summary.average_latency_ms} ms" if summary.average_latency_ms else "暂无"
        )
        self.metric_rag_label.setText(str(summary.rag_hit_events))
        self.metric_tones_label.setText(_format_counter(summary.tone_counts))
        self.metric_tools_label.setText(_format_counter(summary.tool_counts))

        recent = list(reversed(events[-30:]))
        self.metrics_events_table.setRowCount(len(recent))
        for row, event in enumerate(recent):
            self.metrics_events_table.setItem(row, 0, QTableWidgetItem(format_event_time(event)))
            self.metrics_events_table.setItem(
                row,
                1,
                QTableWidgetItem(str(event.get("event_type", ""))),
            )
            self.metrics_events_table.setItem(row, 2, QTableWidgetItem(format_event_brief(event)))
        self.metrics_events_table.resizeRowsToContents()


def _format_counter(counter: dict[str, int]) -> str:
    if not counter:
        return "暂无"
    parts = [f"{name} {count}" for name, count in sorted(counter.items(), key=lambda item: -item[1])]
    return " · ".join(parts[:8])
