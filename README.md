# python-voice-assistant

基于 Python 的智能语音学习助手（课程设计）— AI 与音频模块。

## 功能

- 语音录制与播放（sounddevice）
- 语音识别（OpenAI Whisper，本地）
- 文本智能处理（知识库 + transformers 抽取式问答）
- 语音播报（pyttsx3）
- 命令行端到端演示

## 环境

- Python 3.10+
- Windows / macOS / Linux

```bash
pip install -r requirements-ai.txt
```

## 快速运行

**必须先在本仓库根目录执行**（存在 `ai/` 包）：

```bash
# 无麦克风：文字演示（推荐）
python run_demo.py session --text "什么是死锁？"

# 有麦克风：完整语音链路
python run_demo.py session --seconds 5

# 查看本机录音设备（系统默认输入）
python run_demo.py devices

# 查看帮助
python run_demo.py --help
```

Windows 可双击 `run_demo.bat`。

更多说明见 [ai/README.md](ai/README.md)。

## 目录结构

```text
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
