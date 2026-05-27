# python-voice-assistant

基于 Python 的**语音 AI 虚拟女友**（课程设计）。

## 功能

- **PyQt5 图形界面**：登录、聊天气泡、文字/语音输入
- 语音录制与播放（sounddevice）
- 语音识别（OpenAI Whisper，本地）
- 文本智能处理（知识库 + transformers）
- 语音播报（pyttsx3）
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
python main.py
```

或双击 `run_gui.bat`。无麦克风时用底部文字框发送即可。

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
main.py             # GUI 入口
ui/                 # PyQt5 界面
ai/                 # 核心模块
  audio_io.py       # 录音/播放
  speech_to_text.py # Whisper
  text_process.py   # 文本处理
  text_to_speech.py # TTS
  pipeline.py       # 流程编排
  demo_cli.py       # CLI 入口
models/             # 模型缓存（不提交）
resources/          # 录音文件（不提交）
docs/               # 文档与实验报告
```

## 分工

本仓库当前实现 **成员3：AI + 音频**。GUI 与数据库模块由组员联调接入。

## License

MIT
