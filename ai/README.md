# AI + 音频模块（成员3）

## 安装

**必须先进入 `VoiceAssistant` 目录**（`ai` 包在这一层下面，在上级目录运行会报 `No module named 'ai'`）：

```bash
cd VoiceAssistant
pip install -r requirements-ai.txt
```

也可在项目根用启动脚本（自动切换目录）：

```bash
cd VoiceAssistant
python run_demo.py session --text "什么是死锁？"
# 或双击 run_demo.bat
```

阶段1 仅需：`numpy scipy sounddevice`  
完整功能需安装全部依赖。Whisper **不需要**单独安装 ffmpeg（已用 scipy 读 wav）。

## 没有麦克风时怎么演示？

无麦克风时 `record` / `session` 录到的是静音，**不应**再走「识别→播报」。

推荐直接用文字输入（跳过录音与 Whisper）：

```bash
python -m ai.demo_cli session --text "什么是死锁？"
python -m ai.demo_cli ask --text "什么是死锁？" --speak
```

程序会在录音/识别前检测静音，避免 Whisper 对静音「幻听」后仍 TTS 播报。

## 命令行自测

```bash
cd VoiceAssistant

# 阶段1：录音与播放
python -m ai.demo_cli record --seconds 5 --play

# 阶段2：语音识别（首次会下载模型到 models/）
python -m ai.demo_cli transcribe --path resources/recordings/xxx.wav --model tiny

# 阶段3：文本处理
python -m ai.demo_cli ask --text "什么是死锁？"

# 阶段4：语音播报
python -m ai.demo_cli speak --text "你好，这是语音学习助手。"

# 阶段5：跳过识别，快速演示 NLP+TTS
python -m ai.demo_cli session --text "什么是死锁？" 

# 阶段5：完整链路（需清晰语音）
python -m ai.demo_cli session --seconds 5 --preload
```

## 给成员1（PyQt）的调用示例

```python
from ai.pipeline import run_from_wav, run_full_voice_session
from ai.audio_io import start_recording, stop_recording
from ai.text_process import ProcessMode

# 方式A：固定时长
result = run_full_voice_session(mode=ProcessMode.QA, record_seconds=5.0)

# 方式B：按钮控制录音
start_recording()
# ... 用户点击停止 ...
path = stop_recording()
result = run_from_wav(path, mode=ProcessMode.QA)
```

**注意：** `transcribe`、`process_text`、`run_from_wav` 耗时较长，请在 `QThread` 中调用，通过信号把 `VoiceSessionResult` 传回界面。

## 给成员2（数据库）的字段

`VoiceSessionResult` 中：

- `recognized_text` → 历史表「语音识别结果」
- `reply_text` → 历史表「AI 回复结果」

## 配置

见 `ai/config.py`：`WHISPER_MODEL_NAME`（默认 `base`）、`SAMPLE_RATE`（16000）等。
