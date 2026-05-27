# 本地大模型（Ollama 3B）+ CosyVoice 声音克隆 — 安装说明

## 一、Ollama + qwen2.5:3b（对话）

### 1. 安装 Ollama

从 https://ollama.com 下载 Windows 版并安装。

### 2. 拉取模型

```powershell
ollama pull qwen2.5:3b
```

### 3. 启动服务

一般安装后会自动运行；也可手动：

```powershell
ollama serve
```

### 4. 自检

```powershell
cd VoiceAssistant
python scripts/check_ollama.py
```

配置见 `config/ai_settings.json` 中 `ollama.model`。

---

## 二、CosyVoice（克隆女友声线）

### 1. 克隆仓库到 third_party

```powershell
cd VoiceAssistant
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git third_party/CosyVoice
```

### 2. 安装 CosyVoice 依赖（Windows / CPU）

在 `VoiceAssistant` 目录执行（已在本机验证可用）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_cosyvoice_deps.ps1
```

说明：

- 需 `torch` 与 `torchaudio` 主版本一致（例如均为 2.8.x）。
- `ruamel.yaml` 须 `<0.18`，否则 HyperPyYAML 报错。
- Windows 上 **WeTextProcessing** 难装，可忽略日志 `no frontend is avaliable`，中文仍可合成。
- **无 NVIDIA GPU** 时首次合成约 30～60 秒/句，属正常现象。

### 3. 下载模型（ModelScope）

在 `third_party/CosyVoice` 目录下下载 `CosyVoice2-0.5B` 到 `pretrained_models/CosyVoice2-0.5B`（与 `config/ai_settings.json` 一致）。

### 4. 准备参考音频（声音复刻）

将 **3～10 秒** 清晰女声 wav 复制为：

```text
VoiceAssistant/resources/voice_ref/reference.wav
```

`config/ai_settings.json` 里 `cosyvoice.prompt_text` 需与参考音频朗读内容一致。

### 5. 自检合成

```powershell
python scripts/_run_cosyvoice_test.py
# 或
python scripts/test_cosyvoice.py
```

成功会在 `data/temp/cosyvoice_test.wav` 生成音频，GUI 状态栏 TTS 为 `cosyvoice`。

### 6. TTS 后端

- `tts.backend: "auto"` — 有 reference.wav 且 CosyVoice 就绪则用克隆音，否则 pyttsx3
- `"cosyvoice"` — 强制 CosyVoice
- `"pyttsx3"` — 强制系统音

---

## 三、运行 GUI

```powershell
pip install -r requirements-ai.txt
python main.py
```

状态栏会显示当前 TTS 后端（`cosyvoice` 或 `pyttsx3`）。

---

## 四、目录结构（AI 相关）

```text
config/           # 人设、Ollama/CosyVoice 配置
ai/
  llm/            # Ollama 对话 + 兜底
  tts/            # CosyVoice + pyttsx3
  speech_to_text.py
  audio_io.py
  pipeline.py
scripts/          # check_ollama, cosyvoice_speak
third_party/      # CosyVoice 源码（需自行 clone）
resources/voice_ref/   # reference.wav
```
