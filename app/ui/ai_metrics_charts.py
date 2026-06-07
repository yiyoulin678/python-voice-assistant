from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ai.chart_series import AiMetricsChartSeries, build_metrics_chart_series
from app.ai.stats import load_ai_events


def _configure_matplotlib_fonts() -> None:
    import matplotlib

    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False


class AiMetricsChartsWidget(QWidget):
    """基于 Matplotlib 的 AI 运行指标统计图。"""

    def __init__(self, events_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.events_path = events_path.resolve()
        self._canvas = None
        self._figure = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        toolbar = QWidget(self)
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        button_row = QHBoxLayout()
        self.refresh_button = QPushButton("刷新图表", toolbar)
        self.refresh_button.clicked.connect(self.refresh)
        button_row.addWidget(self.refresh_button)
        button_row.addStretch(1)
        toolbar_layout.addLayout(button_row)

        self.status_label = QLabel("切换到本页后将自动加载图表。", toolbar)
        self.status_label.setWordWrap(True)
        toolbar_layout.addWidget(self.status_label)
        layout.addWidget(toolbar)

        self._chart_host = QWidget(self)
        self._chart_layout = QVBoxLayout(self._chart_host)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._chart_host, 1)

        self._placeholder = QLabel(
            "正在初始化 Matplotlib…\n若未安装请执行：runtime\\python.exe -m pip install matplotlib",
            self._chart_host,
        )
        self._placeholder.setWordWrap(True)
        self._chart_layout.addWidget(self._placeholder)
        self._init_canvas()

    def _init_canvas(self) -> None:
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            self.status_label.setText("未安装 matplotlib，无法显示统计图。")
            return

        _configure_matplotlib_fonts()
        figure = Figure(figsize=(8.0, 6.0), dpi=100)
        canvas = FigureCanvasQTAgg(figure)
        canvas.setMinimumHeight(420)
        self._figure = figure
        self._canvas = canvas
        self._chart_layout.removeWidget(self._placeholder)
        self._placeholder.deleteLater()
        self._placeholder = None
        self._chart_layout.addWidget(canvas)

    def refresh(self, *, event_limit: int = 500) -> None:
        events = load_ai_events(self.events_path, limit=event_limit)
        series = build_metrics_chart_series(events)
        if self._canvas is None or self._figure is None:
            self.status_label.setText(f"已读取 {len(events)} 条事件，但图表组件不可用。")
            return
        self._render(series)
        rag_rate = (
            f"{series.rag_hit_chats}/{series.rag_total_chats}"
            if series.rag_total_chats
            else "0/0"
        )
        self.status_label.setText(
            f"已加载最近 {len(events)} 条事件；知识库命中 {rag_rate} 次对话。"
        )
        self._canvas.draw_idle()

    def _render(self, series: AiMetricsChartSeries) -> None:
        figure = self._figure
        assert figure is not None
        figure.clear()
        axes = figure.subplots(2, 2)
        figure.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.10, hspace=0.42, wspace=0.28)
        figure.suptitle("AI 运行指标统计", fontsize=12)

        daily_ax, event_ax, latency_ax, tool_ax = axes[0][0], axes[0][1], axes[1][0], axes[1][1]
        self._plot_daily_chats(daily_ax, series)
        self._plot_event_types(event_ax, series)
        self._plot_latencies(latency_ax, series)
        self._plot_tools(tool_ax, series)

    def _plot_daily_chats(self, axis, series: AiMetricsChartSeries) -> None:
        axis.set_title("近 7 日对话次数")
        if not series.daily_labels:
            axis.text(0.5, 0.5, "暂无数据", ha="center", va="center")
            axis.set_axis_off()
            return
        axis.bar(series.daily_labels, series.daily_chat_counts, color="#5B8FF9")
        axis.set_ylabel("次数")
        axis.tick_params(axis="x", rotation=35)

    def _plot_event_types(self, axis, series: AiMetricsChartSeries) -> None:
        axis.set_title("事件类型分布")
        if not series.event_type_counts:
            axis.text(0.5, 0.5, "暂无数据", ha="center", va="center")
            axis.set_axis_off()
            return
        axis.pie(
            series.event_type_counts,
            labels=series.event_type_labels,
            autopct="%1.0f%%",
            startangle=90,
            textprops={"fontsize": 8},
        )

    def _plot_latencies(self, axis, series: AiMetricsChartSeries) -> None:
        axis.set_title("最近对话耗时 (ms)")
        if not series.latency_values_ms:
            axis.text(0.5, 0.5, "暂无数据", ha="center", va="center")
            axis.set_axis_off()
            return
        axis.plot(
            range(len(series.latency_values_ms)),
            series.latency_values_ms,
            marker="o",
            color="#61DDAA",
            linewidth=1.5,
        )
        axis.set_ylabel("ms")
        axis.set_xticks(range(len(series.latency_labels)))
        axis.set_xticklabels(series.latency_labels, rotation=45, ha="right", fontsize=7)

    def _plot_tools(self, axis, series: AiMetricsChartSeries) -> None:
        axis.set_title("工具调用 Top5")
        if not series.tool_counts:
            axis.text(0.5, 0.5, "暂无数据", ha="center", va="center")
            axis.set_axis_off()
            return
        y_pos = range(len(series.tool_labels))
        axis.barh(list(y_pos), series.tool_counts, color="#F6BD16")
        axis.set_yticks(list(y_pos))
        axis.set_yticklabels(series.tool_labels)
        axis.invert_yaxis()
        axis.set_xlabel("次数")
