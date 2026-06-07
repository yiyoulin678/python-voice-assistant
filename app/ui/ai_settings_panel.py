from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ai.stats import format_event_brief, format_event_time, load_ai_events, summarize_ai_events
from app.ui.ai_metrics_charts import AiMetricsChartsWidget
from app.config.ai_settings import AiFeatureSettings
from app.platform.open_folder import open_folder_in_file_manager
from app.rag.knowledge_base import KnowledgeBase

_TABLE_MAX_HEIGHT = 150
_EVENTS_TABLE_MAX_HEIGHT = 180


class AiSettingsPanel(QWidget):
    """设置页中的 AI 知识库与运行指标可视化。"""

    def __init__(
        self,
        base_dir: Path,
        ai_settings: AiFeatureSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.base_dir = base_dir.resolve()
        self._ai_settings = (ai_settings or AiFeatureSettings()).normalized()
        self.knowledge_base = KnowledgeBase(self.base_dir)
        self.events_path = self.base_dir / "data" / "metrics" / "ai_events.jsonl"
        self._ready = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 0)
        hint = QLabel("知识库放说明文档；对话结束后可自动写纪要到 data/notes/", header)
        hint.setWordWrap(True)
        header_layout.addWidget(hint, 1)
        self.auto_session_summary_check = QCheckBox("对话结束后自动写纪要", header)
        self.auto_session_summary_check.setChecked(
            self._ai_settings.auto_session_summary_enabled
        )
        header_layout.addWidget(self.auto_session_summary_check)
        self.open_knowledge_dir_button = QPushButton("打开知识库", header)
        self.open_knowledge_dir_button.clicked.connect(self._open_knowledge_dir)
        self.open_metrics_dir_button = QPushButton("打开指标目录", header)
        self.open_metrics_dir_button.clicked.connect(self._open_metrics_dir)
        self.open_summary_notes_button = QPushButton("打开纪要笔记", header)
        self.open_summary_notes_button.clicked.connect(self._open_summary_notes_dir)
        header_layout.addWidget(self.open_knowledge_dir_button)
        header_layout.addWidget(self.open_metrics_dir_button)
        header_layout.addWidget(self.open_summary_notes_button)
        outer.addWidget(header)

        self._sub_tabs = QTabWidget(self)
        self._sub_tabs.addTab(self._build_knowledge_page(), "知识库")
        self._sub_tabs.addTab(self._build_metrics_page(), "运行指标")
        self._charts_widget = AiMetricsChartsWidget(self.events_path, self)
        self._sub_tabs.addTab(wrap_page_scroll(self._charts_widget), "统计图")
        outer.addWidget(self._sub_tabs, 1)

        self._placeholder_label = QLabel("切换到本页后将自动加载数据。", self)
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setContentsMargins(16, 8, 16, 12)
        outer.addWidget(self._placeholder_label)

    def _open_knowledge_dir(self) -> None:
        self._open_data_dir(
            self.base_dir / "data" / "knowledge",
            create=True,
            title="打开知识库文件夹",
        )

    def _open_metrics_dir(self) -> None:
        self._open_data_dir(
            self.base_dir / "data" / "metrics",
            create=True,
            title="打开指标文件夹",
        )

    def _open_logs_dir(self) -> None:
        self._open_data_dir(
            self.base_dir / "data" / "logs",
            create=True,
            title="打开日志文件夹",
        )

    def _open_summary_notes_dir(self) -> None:
        self._open_data_dir(
            self.base_dir / "data" / "notes",
            create=True,
            title="打开纪要笔记文件夹",
        )

    def collect_ai_feature_settings(self) -> AiFeatureSettings:
        return AiFeatureSettings(
            auto_session_summary_enabled=self.auto_session_summary_check.isChecked(),
        ).normalized()

    def _open_data_dir(self, path: Path, *, create: bool, title: str) -> None:
        try:
            opened_path = open_folder_in_file_manager(path, create=create)
        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            QMessageBox.warning(self, title, str(exc))
            return
        self._placeholder_label.setText(f"已在资源管理器中打开：{opened_path}")

    def refresh_on_show(self) -> None:
        if not self._ready:
            self._placeholder_label.setText("正在加载…")
            self._ready = True
        self.refresh_knowledge(rebuild_index=False)
        self.refresh_metrics()
        self._charts_widget.refresh()
        self._placeholder_label.setText("数据已更新。检索较慢时请先点「重建索引」。")

    def _build_knowledge_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.knowledge_status_label = QLabel("尚未加载", page)
        layout.addWidget(self.knowledge_status_label)

        self.knowledge_sources_table = _compact_table(page, ["文档", "片段数"], _TABLE_MAX_HEIGHT)
        layout.addWidget(self.knowledge_sources_table)

        search_layout = QHBoxLayout()
        self.knowledge_search_edit = QLineEdit(page)
        self.knowledge_search_edit.setPlaceholderText("输入问题后回车或点检索")
        self.knowledge_search_edit.returnPressed.connect(self._run_knowledge_search)
        self.knowledge_search_button = QPushButton("检索", page)
        self.knowledge_search_button.clicked.connect(self._run_knowledge_search)
        self.knowledge_reload_button = QPushButton("重建索引", page)
        self.knowledge_reload_button.clicked.connect(self._reload_knowledge_index)
        search_layout.addWidget(self.knowledge_search_edit, 1)
        search_layout.addWidget(self.knowledge_search_button)
        search_layout.addWidget(self.knowledge_reload_button)
        layout.addLayout(search_layout)

        self.knowledge_results_table = _compact_table(
            page,
            ["来源", "相关度", "摘要"],
            _EVENTS_TABLE_MAX_HEIGHT,
        )
        layout.addWidget(self.knowledge_results_table)
        layout.addStretch(1)
        return wrap_page_scroll(page)

    def _build_metrics_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.metrics_refresh_button = QPushButton("刷新", page)
        self.metrics_refresh_button.clicked.connect(self.refresh_metrics)
        self.open_logs_dir_button = QPushButton("打开日志目录", page)
        self.open_logs_dir_button.clicked.connect(self._open_logs_dir)
        toolbar.addWidget(self.metrics_refresh_button)
        toolbar.addWidget(self.open_logs_dir_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        summary_box = QGroupBox("汇总", page)
        grid = QGridLayout(summary_box)
        self.metric_total_label = QLabel("0", summary_box)
        self.metric_chat_label = QLabel("0", summary_box)
        self.metric_retry_label = QLabel("0", summary_box)
        self.metric_latency_label = QLabel("暂无", summary_box)
        self.metric_rag_label = QLabel("0", summary_box)
        self.metric_tones_label = QLabel("暂无", summary_box)
        self.metric_tones_label.setWordWrap(True)
        self.metric_tools_label = QLabel("暂无", summary_box)
        self.metric_tools_label.setWordWrap(True)
        grid.addWidget(QLabel("事件总数"), 0, 0)
        grid.addWidget(self.metric_total_label, 0, 1)
        grid.addWidget(QLabel("完成对话"), 0, 2)
        grid.addWidget(self.metric_chat_label, 0, 3)
        grid.addWidget(QLabel("校验重试"), 1, 0)
        grid.addWidget(self.metric_retry_label, 1, 1)
        grid.addWidget(QLabel("平均耗时"), 1, 2)
        grid.addWidget(self.metric_latency_label, 1, 3)
        grid.addWidget(QLabel("命中知识库"), 2, 0)
        grid.addWidget(self.metric_rag_label, 2, 1)
        grid.addWidget(QLabel("语气分布"), 3, 0)
        grid.addWidget(self.metric_tones_label, 3, 1, 1, 3)
        grid.addWidget(QLabel("工具调用"), 4, 0)
        grid.addWidget(self.metric_tools_label, 4, 1, 1, 3)
        layout.addWidget(summary_box)

        self.metrics_events_table = _compact_table(
            page,
            ["时间", "类型", "摘要"],
            _EVENTS_TABLE_MAX_HEIGHT,
        )
        layout.addWidget(self.metrics_events_table)
        layout.addStretch(1)
        return wrap_page_scroll(page)

    def _reload_knowledge_index(self) -> None:
        self.knowledge_reload_button.setEnabled(False)
        self.knowledge_status_label.setText("正在重建索引…")
        try:
            self.refresh_knowledge(rebuild_index=True)
        finally:
            self.knowledge_reload_button.setEnabled(True)

    def refresh_knowledge(self, *, rebuild_index: bool = False) -> None:
        try:
            chunk_count = self.knowledge_base.reload(force=rebuild_index)
            sources = self.knowledge_base.list_sources()
        except Exception as exc:  # noqa: BLE001
            self.knowledge_status_label.setText(f"知识库加载失败：{exc}")
            return

        self.knowledge_status_label.setText(
            f"{len(sources)} 个文档，{chunk_count} 个片段"
        )

        counts = self.knowledge_base.source_chunk_counts()
        self.knowledge_sources_table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            self.knowledge_sources_table.setItem(row, 0, QTableWidgetItem(source))
            count_item = QTableWidgetItem(str(counts.get(source, 0)))
            count_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.knowledge_sources_table.setItem(row, 1, count_item)

    def _run_knowledge_search(self) -> None:
        query = self.knowledge_search_edit.text().strip()
        if not query:
            self.knowledge_results_table.setRowCount(0)
            return
        self.knowledge_search_button.setEnabled(False)
        try:
            hits = self.knowledge_base.search(query, limit=6)
        except Exception as exc:  # noqa: BLE001
            self.knowledge_results_table.setRowCount(1)
            self.knowledge_results_table.setItem(0, 0, QTableWidgetItem("错误"))
            self.knowledge_results_table.setItem(0, 1, QTableWidgetItem(""))
            self.knowledge_results_table.setItem(0, 2, QTableWidgetItem(str(exc)))
            return
        finally:
            self.knowledge_search_button.setEnabled(True)

        self.knowledge_results_table.setRowCount(len(hits))
        for row, hit in enumerate(hits):
            self.knowledge_results_table.setItem(row, 0, QTableWidgetItem(hit.source))
            score_item = QTableWidgetItem(f"{hit.score:.2f}")
            score_item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.knowledge_results_table.setItem(row, 1, score_item)
            preview = hit.text.replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:119] + "…"
            self.knowledge_results_table.setItem(row, 2, QTableWidgetItem(preview))

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

        recent = list(reversed(events[-20:]))
        self.metrics_events_table.setRowCount(len(recent))
        for row, event in enumerate(recent):
            self.metrics_events_table.setItem(row, 0, QTableWidgetItem(format_event_time(event)))
            self.metrics_events_table.setItem(
                row,
                1,
                QTableWidgetItem(str(event.get("event_type", ""))),
            )
            self.metrics_events_table.setItem(row, 2, QTableWidgetItem(format_event_brief(event)))


def _compact_table(parent: QWidget, headers: list[str], max_height: int) -> QTableWidget:
    table = QTableWidget(0, len(headers), parent)
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(True)
    table.setMaximumHeight(max_height)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    if len(headers) > 1:
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    return table


def wrap_page_scroll(page: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    return scroll


def _format_counter(counter: dict[str, int]) -> str:
    if not counter:
        return "暂无"
    parts = [f"{name} {count}" for name, count in sorted(counter.items(), key=lambda item: -item[1])]
    return " · ".join(parts[:6])
