"""虚拟女友 — 主聊天界面。"""
from __future__ import annotations

import html
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ai import audio_io
from ai.text_process import ProcessMode
from ui.workers import PreloadWorker, StopRecordAndProcessWorker, TextChatWorker

ASSISTANT_NAME = "小音"
ASSISTANT_TITLE = "你的语音 AI 伙伴"


class ChatWindow(QMainWindow):
    def __init__(self, username: str = "用户") -> None:
        super().__init__()
        self.username = username.strip() or "用户"
        self._recording = False
        self._busy = False
        self._worker = None

        self.setWindowTitle(f"{ASSISTANT_NAME} — 语音 AI 虚拟女友")
        self.resize(520, 720)
        self._build_ui()
        self._start_preload()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        # 顶栏：角色信息
        header = QWidget()
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #ff9a9e, stop:1 #fecfef); border-radius: 12px; padding: 8px;"
        )
        hl = QVBoxLayout(header)
        self.lbl_name = QLabel(f"💗 {ASSISTANT_NAME}")
        self.lbl_name.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.lbl_sub = QLabel(f"{ASSISTANT_TITLE}　·　你好，{html.escape(self.username)}")
        self.lbl_sub.setStyleSheet("color: #333;")
        self.lbl_status = QLabel("正在加载 AI 模型，请稍候…")
        self.lbl_status.setStyleSheet("color: #555; font-size: 11px;")
        hl.addWidget(self.lbl_name)
        hl.addWidget(self.lbl_sub)
        hl.addWidget(self.lbl_status)
        root.addWidget(header)

        # 对话区
        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setStyleSheet(
            "QTextBrowser { background: #f5f5f5; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px; }"
        )
        root.addWidget(self.chat, stretch=1)

        self._append_system(
            f"我是{ASSISTANT_NAME}～你可以按住「说话」用语音聊天，或在下面输入文字。"
            "没有麦克风时，直接打字发送即可。"
        )

        # 选项
        opts = QHBoxLayout()
        self.chk_speak = QCheckBox("自动语音播报回复")
        self.chk_speak.setChecked(True)
        opts.addWidget(self.chk_speak)
        opts.addStretch()
        root.addLayout(opts)

        # 文字输入
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入想说的话，按 Enter 发送…")
        self.input.returnPressed.connect(self._on_send_text)
        self.btn_send = QPushButton("发送")
        self.btn_send.clicked.connect(self._on_send_text)
        input_row.addWidget(self.input, stretch=1)
        input_row.addWidget(self.btn_send)
        root.addLayout(input_row)

        # 语音按钮
        voice_row = QHBoxLayout()
        self.btn_talk = QPushButton("🎤 按住说话")
        self.btn_talk.setMinimumHeight(48)
        self.btn_talk.setStyleSheet(
            "QPushButton { background: #ff6b9d; color: white; border-radius: 24px; font-size: 14px; }"
            "QPushButton:pressed { background: #e85a8a; }"
            "QPushButton:disabled { background: #ccc; }"
        )
        self.btn_talk.pressed.connect(self._on_talk_pressed)
        self.btn_talk.released.connect(self._on_talk_released)

        self.btn_toggle_rec = QPushButton("开始录音")
        self.btn_toggle_rec.setMinimumHeight(48)
        self.btn_toggle_rec.clicked.connect(self._on_toggle_record)

        voice_row.addWidget(self.btn_talk, stretch=2)
        voice_row.addWidget(self.btn_toggle_rec, stretch=1)
        root.addLayout(voice_row)

        self._set_busy(True, "正在加载 AI 模型…")

    def _start_preload(self) -> None:
        self._worker = PreloadWorker(self)
        self._worker.finished_ok.connect(self._on_preload_ok)
        self._worker.failed.connect(self._on_preload_fail)
        self._worker.start()

    def _on_preload_ok(self) -> None:
        self._set_busy(False, "在线 · 可以开始聊天了")
        self._append_system("模型已就绪，开始聊天吧～")

    def _on_preload_fail(self, msg: str) -> None:
        self._set_busy(False, f"模型未完全加载（可仍用文字聊天）")
        self._append_system(f"预加载提示：{msg}")

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self._busy = busy
        self.btn_send.setEnabled(not busy)
        self.btn_talk.setEnabled(not busy)
        self.btn_toggle_rec.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if status is not None:
            self.lbl_status.setText(status)

    def _speak_enabled(self) -> bool:
        return self.chk_speak.isChecked()

    def _append_system(self, text: str) -> None:
        t = datetime.now().strftime("%H:%M")
        safe = html.escape(text)
        block = (
            f'<p style="text-align:center; color:#888; font-size:11px; margin:6px 0;">'
            f'<span style="background:#eee; padding:4px 10px; border-radius:10px;">'
            f"{t} · {safe}</span></p>"
        )
        self.chat.append(block)

    def _append_message(self, text: str, is_user: bool) -> None:
        t = datetime.now().strftime("%H:%M")
        safe = html.escape(text).replace("\n", "<br/>")
        if is_user:
            bubble = "#95ec69"
            align = "right"
            who = html.escape(self.username)
        else:
            bubble = "#ffffff"
            align = "left"
            who = ASSISTANT_NAME
        block = (
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:8px 0;">'
            f'<tr><td style="text-align:{align};">'
            f'<span style="font-size:10px;color:#999;">{who} · {t}</span><br/>'
            f'<span style="display:inline-block; max-width:85%; text-align:left; '
            f"background:{bubble}; padding:10px 14px; border-radius:12px; "
            f'border:1px solid #e0e0e0;">{safe}</span>'
            f"</td></tr></table>"
        )
        self.chat.append(block)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _on_send_text(self) -> None:
        text = self.input.text().strip()
        if not text or self._busy:
            return
        self.input.clear()
        self._append_message(text, is_user=True)
        self._run_text_chat(text)

    def _run_text_chat(self, text: str) -> None:
        self._set_busy(True, "正在思考…")
        worker = TextChatWorker(
            text,
            speak_reply=self._speak_enabled(),
            mode=ProcessMode.QA,
            parent=self,
        )
        worker.status.connect(self.lbl_status.setText)
        worker.finished.connect(self._on_pipeline_finished)
        self._worker = worker
        worker.start()

    def _on_talk_pressed(self) -> None:
        if self._busy or self._recording:
            return
        try:
            audio_io.start_recording()
            self._recording = True
            self.lbl_status.setText("正在听…松开结束")
            self.btn_talk.setText("🔴 松开结束")
        except audio_io.AudioIOError as exc:
            QMessageBox.warning(self, "录音失败", str(exc))

    def _on_talk_released(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self.btn_talk.setText("🎤 按住说话")
        self._set_busy(True, "处理中…")
        worker = StopRecordAndProcessWorker(
            speak_reply=self._speak_enabled(),
            parent=self,
        )
        worker.status.connect(self.lbl_status.setText)
        worker.finished.connect(self._on_pipeline_finished)
        self._worker = worker
        worker.start()

    def _on_toggle_record(self) -> None:
        if self._busy:
            return
        if not self._recording:
            try:
                audio_io.start_recording()
                self._recording = True
                self.btn_toggle_rec.setText("结束并发送")
                self.lbl_status.setText("录音中…")
            except audio_io.AudioIOError as exc:
                QMessageBox.warning(self, "录音失败", str(exc))
        else:
            self._recording = False
            self.btn_toggle_rec.setText("开始录音")
            self._set_busy(True, "处理中…")
            worker = StopRecordAndProcessWorker(
                speak_reply=self._speak_enabled(),
                parent=self,
            )
            worker.status.connect(self.lbl_status.setText)
            worker.finished.connect(self._on_pipeline_finished)
            self._worker = worker
            worker.start()

    def _on_pipeline_finished(self, result) -> None:
        self._set_busy(False, "在线 · 可以开始聊天了")
        # 语音流程：展示识别出的用户原话；文字聊天已在发送时展示过
        if result.recording_path and result.recognized_text:
            self._append_message(result.recognized_text, is_user=True)
        if result.success and result.reply_text:
            self._append_message(result.reply_text, is_user=False)
        elif result.error_message:
            self._append_system(f"提示：{result.error_message}")
            if "未检测到有效语音" in result.error_message:
                self._append_system("没有麦克风时，请使用下方文字输入框发送消息。")

    def closeEvent(self, event) -> None:
        if self._recording:
            try:
                audio_io.stop_recording()
            except Exception:
                pass
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        super().closeEvent(event)
