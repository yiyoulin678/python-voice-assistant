# Qwen3-TTS（可选，已默认关闭）

小音已改用 VoxCPM，见 [SETUP_VOXCPM.md](SETUP_VOXCPM.md)。以下为 Qwen 备用说明。

## 使用 Qwen TTS WebUI 整合包（推荐，已配置）

若本机已有 [Qwen TTS WebUI](https://github.com/licyk/qwen_tts_webui) 整合包，在 `config/ai_settings.json` 中设置：

```json
"webui_root": "D:/Game/Qwen_TTS/.../qwen_tts_webui-licyk-20260525",
"use_webui_api": true,
"api_url": "http://127.0.0.1:7861",
"auto_start_api": true,
"clone_model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
```

- 对接 WebUI **官方 HTTP API**（`--api --nowebui`），与 GPT-SoVITS 的 `api_v2` 思路相同。
- 接口：`POST /qwenapi/v1/voice-clone`（克隆）、`/qwenapi/v1/custom-voice`（预设声线）。
- 文档：浏览器地址栏是多少端口，`api_url` 就写多少（例如 `http://127.0.0.1:7861/docs`）
- 7860 被占用时 WebUI 会自动改用 7861，小音若仍写 7860 会连错服务
- 手动启动：`scripts/start_qwen_tts_api.bat`（或小音 `auto_start_api: true` 自动拉起）

## 仅用 pip（无 WebUI）

```powershell
pip install qwen-tts soundfile
```

将 `use_webui_python` 设为 `false`，并删除或留空 `webui_root`。

## 两种模式（`config/ai_settings.json` → `qwen_tts`）

### 1. custom_voice（默认，推荐）

- 模型：`Qwen3-TTS-12Hz-0.6B-CustomVoice`（约 0.6B，CPU 可跑）
- 内置说话人：`Serena`（温柔女声）、`Vivian` 等
- 可用 `instruct` 微调语气（虚拟女友风格）
- **不需要** reference.wav

### 2. clone（声音克隆）

```json
"mode": "clone",
"x_vector_only_mode": true,
"clone_model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
```

- `x_vector_only_mode: true`：只需参考音频，**不必填台词**（音质略低）。
- `false` 时需 `prompt_text` 与录音内容一致。

## 自检

```powershell
python scripts/check_qwen_tts.py
```

首次运行会从 Hugging Face / ModelScope 下载模型，请保持网络畅通。

## 优先级（`tts.backend: auto`）

1. Qwen3-TTS  
2. CosyVoice  
3. pyttsx3  

GPT-SoVITS 已默认关闭（`gpt_sovits.enabled: false`）。
