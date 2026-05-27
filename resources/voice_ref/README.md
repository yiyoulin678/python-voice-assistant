# 声音克隆参考音频

## 方式一：GUI 里现场克隆（推荐）

1. 打开小音 GUI  
2. 点 **「选择克隆音频」**  
3. 选你的 wav/mp3（建议 **3～10 秒**、安静、单人清晰人声）  
4. **不用填台词**，等「声线已注册」后即可聊天  

（当前 `x_vector_only_mode: true`，只根据音色克隆。若以后要更逼真，可在配置里改为 `false` 并填写与录音一致的文字。）

当前配置为 **Qwen3-TTS clone 模式**，声线会缓存在内存里，**不用每句话重新克隆**。

模型来自本机 **Qwen TTS WebUI 整合包**，通过其 **HTTP API** 合成。`api_url` 端口须与浏览器地址栏一致（如 `7861` → `http://127.0.0.1:7861`）。

**加载时间**：当前为 **1.7B** 克隆模型，首次载入显卡约 **1～3 分钟**（有 RTX 4070 等独显时）；启动后会在**后台**加载，界面可先文字聊天。若仍嫌慢，可在 WebUI 里另下载 **0.6B-Base** 并把配置里的 `clone_model_id` 改为 `Qwen/Qwen3-TTS-12Hz-0.6B-Base`。

## 方式二：手动放文件

复制为 `reference.wav`，并在 `config/ai_settings.json` 里设置一致的 `qwen_tts.prompt_text`。

## 配置说明（`config/ai_settings.json` → `qwen_tts`）

| 字段 | 说明 |
|------|------|
| `mode` | `clone` = 用你的音频；`custom_voice` = 内置 Serena 等 |
| `x_vector_only_mode` | `true` = 只给音频、不填台词也能克隆（音质略低） |
| `prompt_text` | 与参考音频朗读内容一致时效果最好 |
