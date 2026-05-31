"""虚拟女友 — 主聊天界面。"""
from __future__ import annotations

import html
from datetime import datetime, time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
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
from ai.tts.speaker import get_tts_backend_name, get_tts_status_label
from ui.workers import (
    PreloadWorker,
    RegisterCloneWorker,
    StartRecordingWorker,
    StopRecordAndProcessWorker,
    TextChatWorker,
    TtsPreviewWorker,
    TtsWarmupWorker,
)
from db.database import DatabaseManager

ASSISTANT_NAME = "小音"
ASSISTANT_TITLE = "你的语音 AI 伙伴"

class ChatWindow(QMainWindow):

    def _load_history(self):

        db = DatabaseManager()

        history = db.get_history(self.user_id)

        for speech_text, ai_response, create_time in history:

            self._append_message(speech_text, is_user=True, time=create_time)
            self._append_message(ai_response, is_user=False, time=create_time)

    def __init__(self, user_id, username) -> None:
        super().__init__()
        self.user_id = user_id
        self.username = username.strip() or "用户"
        self._recording = False
        self._busy = False
        self._worker = None
        self._llm_label = "加载中…"
        self._tts_label = "加载中…"
        self._tts_ready = False
        self._tts_worker = None
        self._rec_starting = False
        self._rec_cancel = False

        self.setWindowTitle(f"{ASSISTANT_NAME} — 语音 AI 虚拟女友")
        self.resize(520, 720)
        self._build_ui()
        self._load_history()
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
        self.lbl_llm = QLabel("对话：检测中…")
        self.lbl_llm.setStyleSheet("color: #5c6bc0; font-size: 11px; font-weight: bold;")
        self.lbl_voice = QLabel("声线：检测中…")
        self.lbl_voice.setStyleSheet("color: #c2185b; font-size: 11px; font-weight: bold;")
        self.lbl_status = QLabel("正在加载 AI 模型，请稍候…")
        self.lbl_status.setStyleSheet("color: #555; font-size: 11px;")
        hl.addWidget(self.lbl_name)
        hl.addWidget(self.lbl_sub)
        hl.addWidget(self.lbl_llm)
        hl.addWidget(self.lbl_voice)
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

        # 音频设备
        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("麦克风:"))
        self.combo_input = QComboBox()
        self.combo_input.setMinimumWidth(180)
        self.combo_input.currentIndexChanged.connect(self._on_input_device_changed)
        dev_row.addWidget(self.combo_input, stretch=1)
        dev_row.addWidget(QLabel("播放:"))
        self.combo_output = QComboBox()
        self.combo_output.setMinimumWidth(180)
        self.combo_output.currentIndexChanged.connect(self._on_output_device_changed)
        dev_row.addWidget(self.combo_output, stretch=1)
        self.btn_refresh_devices = QPushButton("刷新")
        self.btn_refresh_devices.setToolTip("重新扫描系统音频设备")
        self.btn_refresh_devices.clicked.connect(self._refresh_audio_devices)
        dev_row.addWidget(self.btn_refresh_devices)
        root.addLayout(dev_row)
        self._refresh_audio_devices(select_saved=True)

        # 选项：克隆播报 + 试听
        opts = QHBoxLayout()
        self.chk_speak = QCheckBox("自动语音播报回复（VoxCPM 女友声线）")
        self.chk_speak.setChecked(True)
        self.chk_speak.setToolTip(
            "优先使用 VoxCPM 声音克隆；不可用时尝试 CosyVoice 或系统语音。"
        )
        self.btn_preview = QPushButton("试听声线")
        self.btn_preview.setToolTip("播放一句示例，确认当前克隆/系统播报是否正常")
        self.btn_preview.clicked.connect(self._on_preview_voice)
        self.btn_preview.setEnabled(False)
        self.btn_clone = QPushButton("选择克隆音频")
        self.btn_clone.setEnabled(False)
        self.btn_clone.setToolTip(
            "选一段 3～10 秒清晰人声即可克隆，无需填写台词。"
        )
        self.btn_clone.clicked.connect(self._on_pick_clone_audio)
        opts.addWidget(self.chk_speak)
        opts.addWidget(self.btn_clone)
        opts.addWidget(self.btn_preview)
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

    def _refresh_audio_devices(self, select_saved: bool = False) -> None:
        """填充麦克风 / 播放设备下拉框。"""
        if select_saved:
            cur_in = audio_io.get_input_device()
            cur_out = audio_io.get_output_device()
        elif hasattr(self, "combo_input") and self.combo_input.count() > 0:
            cur_in = self.combo_input.currentData()
            cur_out = self.combo_output.currentData()
        else:
            cur_in = audio_io.get_input_device()
            cur_out = audio_io.get_output_device()

        def _fill(combo: QComboBox, devices: list[dict], current: int | None) -> None:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("系统默认", None)
            select_idx = 0
            for i, dev in enumerate(devices, start=1):
                combo.addItem(audio_io.device_combo_label(dev), dev["index"])
                if current is not None and dev["index"] == current:
                    select_idx = i
            combo.setCurrentIndex(select_idx)
            combo.blockSignals(False)

        try:
            inputs = audio_io.list_input_devices()
            outputs = audio_io.list_output_devices()
        except audio_io.AudioIOError as exc:
            QMessageBox.warning(self, "音频设备", str(exc))
            return

        _fill(self.combo_input, inputs, cur_in)
        _fill(self.combo_output, outputs, cur_out)

    def _on_input_device_changed(self, _index: int) -> None:
        if not hasattr(self, "combo_input"):
            return
        try:
            audio_io.set_input_device(self.combo_input.currentData())
        except audio_io.AudioIOError as exc:
            QMessageBox.warning(self, "麦克风", str(exc))

    def _on_output_device_changed(self, _index: int) -> None:
        if not hasattr(self, "combo_output"):
            return
        try:
            audio_io.set_output_device(self.combo_output.currentData())
        except audio_io.AudioIOError as exc:
            QMessageBox.warning(self, "播放设备", str(exc))

    def _start_preload(self) -> None:
        self._worker = PreloadWorker(self)
        self._worker.status.connect(self.lbl_status.setText)
        self._worker.finished_ok.connect(self._on_preload_ok)
        self._worker.failed.connect(self._on_preload_fail)
        self._worker.start()

    def _online_status(self) -> str:
        return f"在线 · 对话: {self._llm_label} · 播报: {self._tts_label}"

    def _refresh_llm_badge(self) -> None:
        from ai.llm import ollama_client

        label = ollama_client.get_status_label()
        self._llm_label = label
        if ollama_client.is_available() and ollama_client.ensure_model_pulled():
            self.lbl_llm.setText(f"对话：{label} ✓")
            self.lbl_llm.setStyleSheet("color: #2e7d32; font-size: 11px; font-weight: bold;")
        else:
            self.lbl_llm.setText(f"对话：{label}（规则兜底）")
            self.lbl_llm.setStyleSheet("color: #e65100; font-size: 11px; font-weight: bold;")

    def _refresh_voice_badge(self) -> None:
        backend = get_tts_backend_name()
        label = get_tts_status_label()
        if backend in ("voxcpm", "qwen_tts", "cosyvoice", "gpt_sovits"):
            self.lbl_voice.setText(f"声线：{label} ✓")
            self.lbl_voice.setStyleSheet("color: #c2185b; font-size: 11px; font-weight: bold;")
            self.chk_speak.setText(f"自动语音播报（{label}）")
        else:
            self.lbl_voice.setText("声线：系统语音 (pyttsx3)")
            self.lbl_voice.setStyleSheet("color: #666; font-size: 11px;")
            self.chk_speak.setText("自动语音播报回复（系统语音）")

    def _on_preload_ok(self, combined: str) -> None:
        if "|" in combined:
            self._llm_label, self._tts_label = combined.split("|", 1)
        else:
            self._tts_label = combined
        self._refresh_llm_badge()
        self._refresh_voice_badge()
        self._set_busy(False, self._online_status())
        self.btn_preview.setEnabled(True)
        self.btn_clone.setEnabled(True)

        from ai.config import VOXCPM_MODE, VOXCPM_PRELOAD_ON_STARTUP, VOXCPM_REFERENCE_WAV
        from ai.llm import ollama_client
        from ai.tts.backends import voxcpm_backend

        backend = get_tts_backend_name()
        need_tts_bg = (
            VOXCPM_PRELOAD_ON_STARTUP
            and backend == "voxcpm"
            and voxcpm_backend.is_available()
            and not (
                (VOXCPM_MODE or "").lower() == "clone"
                and not VOXCPM_REFERENCE_WAV.is_file()
            )
        )
        if need_tts_bg:
            self._tts_ready = False
            self._start_tts_warmup()
            self._append_system(
                "界面已可用。VoxCPM 正在后台载入显卡（首次约 1～2 分钟）；"
                "完成前可先文字聊天。"
            )
        else:
            self._tts_ready = True

        if ollama_client.is_available() and ollama_client.ensure_model_pulled():
            if not need_tts_bg:
                self._append_system(
                    "模型已就绪～对话走本地 Ollama，回复可走 VoxCPM 克隆声线（见顶栏状态）。"
                )
        else:
            self._append_system(
                "语音识别已就绪；Ollama 未连接时对话为规则兜底。"
                "请保持 ollama serve 运行并拉取 qwen2.5:3b 后重启。"
            )

    def _start_tts_warmup(self) -> None:
        if self._tts_worker is not None and self._tts_worker.isRunning():
            return
        self._tts_label = "VoxCPM 加载中…"
        self._refresh_voice_badge()
        self.lbl_status.setText("VoxCPM 后台加载中，可先文字聊天…")
        self._tts_worker = TtsWarmupWorker(self)
        self._tts_worker.status.connect(self.lbl_status.setText)
        self._tts_worker.finished_ok.connect(self._on_tts_warmup_ok)
        self._tts_worker.failed.connect(self._on_tts_warmup_fail)
        self._tts_worker.start()

    def _on_tts_warmup_ok(self, label: str) -> None:
        self._tts_label = label
        self._tts_ready = True
        self._refresh_voice_badge()
        self.lbl_status.setText(self._online_status())
        self._append_system("VoxCPM 已就绪，可以语音播报了～")

    def _on_tts_warmup_fail(self, msg: str) -> None:
        self._tts_ready = True
        self._refresh_llm_badge()
        self._refresh_voice_badge()
        self.lbl_status.setText(self._online_status())
        self._append_system(f"VoxCPM 加载失败，已切换备用播报：{msg}")

    def _on_preload_fail(self, msg: str) -> None:
        self._llm_label = "未检测"
        self._tts_label = "播报未检测"
        self._tts_ready = True
        self._refresh_llm_badge()
        self._refresh_voice_badge()
        self._set_busy(False, "模型未完全加载（可仍用文字聊天）")
        self.btn_preview.setEnabled(True)
        self.btn_clone.setEnabled(True)
        self._append_system(f"预加载提示：{msg}")

    def _on_pick_clone_audio(self) -> None:
        if self._busy:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择参考音频（建议 3～10 秒清晰人声）",
            "",
            "音频 (*.wav *.mp3 *.flac *.m4a);;所有文件 (*.*)",
        )
        if not path:
            return
        from ai.config import VOXCPM_X_VECTOR_ONLY

        prompt = ""
        if not VOXCPM_X_VECTOR_ONLY:
            text, ok = QInputDialog.getText(
                self,
                "参考音频台词（必填）",
                "请填写与录音完全一致的文字：",
            )
            if not ok or not text.strip():
                return
            prompt = text.strip()
        self._set_busy(True, "正在注册克隆声线（无需台词，仅提取音色）…")
        worker = RegisterCloneWorker(path, prompt, parent=self)
        worker.status.connect(self.lbl_status.setText)
        worker.finished.connect(self._on_clone_registered)
        self._worker = worker
        worker.start()

    def _on_clone_registered(self, ok: bool, detail: str) -> None:
        self._refresh_voice_badge()
        self._set_busy(False, self._online_status())
        if ok:
            self._tts_label = detail
            self._append_system(f"已用你的音频注册克隆声线：{detail}。之后回复都会用这个声音。")
        else:
            self._append_system(f"克隆声线注册失败：{detail}")

    def _on_preview_voice(self) -> None:
        if self._busy:
            return
        self._set_busy(True, "正在试听…")
        worker = TtsPreviewWorker(parent=self)
        worker.status.connect(self.lbl_status.setText)
        worker.finished.connect(self._on_preview_finished)
        self._worker = worker
        worker.start()

    def _on_preview_finished(self, ok: bool, detail: str) -> None:
        self._set_busy(False, self._online_status())
        if ok:
            self._append_system(f"试听完成（{detail} 克隆/系统播报）。")
        else:
            self._append_system(f"试听失败：{detail}")

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self._busy = busy
        self.btn_send.setEnabled(not busy)
        self.btn_talk.setEnabled(not busy)
        self.btn_toggle_rec.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if status is not None:
            self.lbl_status.setText(status)

    def _speak_enabled(self) -> bool:
        if not self.chk_speak.isChecked():
            return False
        if not self._tts_ready and get_tts_backend_name() in ("voxcpm", "qwen_tts"):
            return False
        return True

    def _append_system(self, text: str) -> None:
        t = datetime.now().strftime("%H:%M")
        safe = html.escape(text)
        block = (
            f'<p style="text-align:center; color:#888; font-size:11px; margin:6px 0;">'
            f'<span style="background:#eee; padding:4px 10px; border-radius:10px;">'
            f"{t} · {safe}</span></p>"
        )
        self.chat.append(block)

    def _append_message(self, text: str, is_user: bool,time = None) -> None:
        
        if time is None:
            t = datetime.now().strftime("%H:%M")
        else:
            t = time[:16]
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
            user_id=self.user_id,
            speak_reply=self._speak_enabled(),
            mode=ProcessMode.QA,
            user_nickname=self.username,
            parent=self,
        )
        worker.status.connect(self.lbl_status.setText)
        worker.finished.connect(self._on_pipeline_finished)
        self._worker = worker
        worker.start()

    def _on_talk_pressed(self) -> None:
        if self._busy or self._recording or self._rec_starting:
            return
        self._rec_starting = True
        self._rec_cancel = False
        self.lbl_status.setText("正在打开麦克风…")
        worker = StartRecordingWorker(self)
        worker.finished.connect(self._on_recording_started)
        worker.start()

    def _on_recording_started(self, ok: bool, message: str) -> None:
        self._rec_starting = False
        if self._rec_cancel:
            self._rec_cancel = False
            if ok:
                try:
                    audio_io.stop_recording()
                except audio_io.AudioIOError:
                    pass
            self.btn_talk.setText("🎤 按住说话")
            self.lbl_status.setText(self._online_status())
            return
        if not ok:
            QMessageBox.warning(self, "录音失败", message or "无法打开麦克风")
            self.btn_talk.setText("🎤 按住说话")
            self.lbl_status.setText(self._online_status())
            return
        self._recording = True
        self.lbl_status.setText("正在听…松开结束")
        self.btn_talk.setText("🔴 松开结束")

    def _on_talk_released(self) -> None:
        if self._rec_starting:
            self._rec_cancel = True
            self.lbl_status.setText("正在取消…")
            return
        if not self._recording:
            return
        self._recording = False
        self.btn_talk.setText("🎤 按住说话")
        self._set_busy(True, "处理中…")
        worker = StopRecordAndProcessWorker(
            user_id=self.user_id,
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
            if self._rec_starting:
                return
            self._rec_starting = True
            self._rec_cancel = False
            self.lbl_status.setText("正在打开麦克风…")

            def _on_toggle_start(ok: bool, message: str) -> None:
                self._rec_starting = False
                if not ok:
                    QMessageBox.warning(self, "录音失败", message or "无法打开麦克风")
                    self.lbl_status.setText(self._online_status())
                    return
                self._recording = True
                self.btn_toggle_rec.setText("结束并发送")
                self.lbl_status.setText("录音中…")

            worker = StartRecordingWorker(self)
            worker.finished.connect(_on_toggle_start)
            worker.start()
        else:
            self._recording = False
            self.btn_toggle_rec.setText("开始录音")
            self._set_busy(True, "处理中…")
            worker = StopRecordAndProcessWorker(
                user_id=self.user_id,
                speak_reply=self._speak_enabled(),
                parent=self,
            )
            worker.status.connect(self.lbl_status.setText)
            worker.finished.connect(self._on_pipeline_finished)
            self._worker = worker
            worker.start()

    def _on_pipeline_finished(self, result) -> None:
        self._set_busy(False, self._online_status())
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

    
