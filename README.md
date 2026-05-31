# python-voice-assistant

基于 Python 的**语音 AI 虚拟女友**（课程设计）。

## 功能

- **PyQt5 图形界面**：登录、聊天气泡、文字/语音输入
- **本地对话**：Ollama + `qwen2.5:3b`（虚拟女友人设）
- **声音克隆**：VoxCPM（参考 `reference.wav`，可选 CosyVoice 兜底）
- 语音识别（Whisper）
- 语音播报（VoxCPM 优先，CosyVoice / pyttsx3 兜底）
- 命令行端到端演示

## 环境

- Python 3.10+
- Windows / macOS / Linux

```bash
pip install -r requirements-ai.txt
```

## 快速运行

### GUI（推荐）

```bash
pip install -r requirements-ai.txt
powershell -ExecutionPolicy Bypass -File scripts/install_voxcpm.ps1
ollama pull qwen2.5:3b
python scripts/check_voxcpm.py
python main.py
```

或双击 `run_gui.bat`。VoxCPM 安装见 [docs/SETUP_VOXCPM.md](docs/SETUP_VOXCPM.md)。

### 命令行

```bash
python run_demo.py session --text "你好"
python run_demo.py session --seconds 5
python run_demo.py devices
```

Windows CLI：双击 `run_demo.bat`。

更多说明见 [ai/README.md](ai/README.md)。

## 目录结构

```text
main.py
config/             # 人设 persona_default.json、ai_settings.json
ui/                 # PyQt5 界面
ai/
  llm/              # Ollama 对话 + 规则兜底
  tts/              # VoxCPM + CosyVoice + pyttsx3
  audio_io.py
  speech_to_text.py
  pipeline.py
scripts/            # check_ollama、cosyvoice_speak
third_party/        # CosyVoice 源码（需 clone）
resources/voice_ref/  # reference.wav 参考音色
docs/SETUP_LLM_TTS.md
```

## 分工

本仓库当前实现 **成员3：AI + 音频**。GUI 与数据库模块由组员联调接入。

## License

MIT
