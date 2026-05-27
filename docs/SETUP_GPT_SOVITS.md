# GPT-SoVITS 接入说明

小音 GUI 通过 **HTTP API** 调用你本机已安装的 GPT-SoVITS（`api_v2.py`，默认端口 `9880`）。

## 1. 配置安装路径

编辑 `config/ai_settings.json`：

```json
"gpt_sovits": {
  "enabled": true,
  "install_dir": "D:/Game/GPT-SoVITS/GPT-SoVITS-v2pro-20250604",
  "api_url": "http://127.0.0.1:9880",
  "auto_start_api": true,
  "reference_wav": "resources/voice_ref/reference.wav",
  "prompt_text": "与 reference.wav 朗读内容完全一致",
  "text_lang": "zh",
  "prompt_lang": "zh"
}
```

也可填相对路径，例如 `third_party/GPT-SoVITS`（需把仓库放到该目录）。

## 2. 准备参考音频

与 CosyVoice 相同：3～10 秒干声 → `resources/voice_ref/reference.wav`，`prompt_text` 与录音一致。

若你已 **训练好角色模型**，在 GPT-SoVITS 的 `GPT_SoVITS/configs/tts_infer.yaml` 里配置好权重后，启动 `api_v2.py` 即可，本程序会调用该配置里的模型。

## 3. 启动 API

**方式 A**（推荐）：双击 `run_gui.bat`，会自动尝试启动 API。

**方式 B**：在 GPT-SoVITS 目录运行：

```powershell
python api_v2.py -a 127.0.0.1 -p 9880
```

或运行 `scripts/start_gpt_sovits_api.bat`。

## 4. 自检

```powershell
cd VoiceAssistant
python scripts/check_gpt_sovits.py
```

## 5. TTS 优先级（`tts.backend: auto`）

1. GPT-SoVITS（API 可用）
2. CosyVoice
3. pyttsx3 系统音

强制指定：`"backend": "gpt_sovits"`。
