# VoxCPM 接入说明

小音默认使用 **[VoxCPM](https://github.com/OpenBMB/VoxCPM)**（清华 OpenBMB），进程内直接合成，无需单独 WebUI / API。

## 1. 克隆仓库

```powershell
cd third_party
git clone --depth 1 https://github.com/OpenBMB/VoxCPM.git VoxCPM
```

GitHub 不稳定时可试镜像：

```powershell
git clone --depth 1 https://gitclone.com/github.com/OpenBMB/VoxCPM.git VoxCPM
```

## 2. 安装

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_voxcpm.ps1
```

或手动：

```powershell
pip install -e third_party/VoxCPM
```

需要 **Python 3.10+**、**PyTorch 2.5+**、**CUDA 12+**（独显推荐）。RTX 4070 建议用 **VoxCPM1.5**（约 6GB 显存，中英克隆快）。

## 配置（`config/ai_settings.json` → `voxcpm`）

```json
"voxcpm": {
  "enabled": true,
  "model_id": "openbmb/VoxCPM1.5",
  "mode": "clone",
  "x_vector_only_mode": true,
  "reference_wav": "resources/voice_ref/reference.wav"
}
```

### 模式

| mode | 说明 |
|------|------|
| `clone` | 用 `reference.wav` 克隆（GUI「选择克隆音频」） |
| `design` | 用文字描述声线，无需参考音频（见 `voice_design_prefix`） |

### 模型选择

| 模型 | 显存 | 特点 |
|------|------|------|
| `openbmb/VoxCPM1.5` | ~6GB | 中英，RTF 快，**默认** |
| `openbmb/VoxCPM2` | ~8GB | 30 语、声音设计、`x_vector_only` 无台词克隆 |

本地已下载时可设：

```json
"local_model_dir": "D:/models/VoxCPM1.5"
```

## 速度调优（`voxcpm`）

| 参数 | 默认（极速） | 说明 |
|------|-------------|------|
| `inference_timesteps` | `4` | 扩散步数，越小越快；`6~10` 音质更好 |
| `retry_badcase` | `false` | 关闭内置 badcase 重试（最多 3 次，很慢） |
| `max_len` | `1024` | 单次生成 token 上限 |
| `tts_max_chars` | `120` | 单次播报最大字数，控制合成时长 |

测速：`python scripts/bench_voxcpm_speed.py`

## 自检

```powershell
python scripts/check_voxcpm.py
```

## 优先级（`tts.backend: auto`）

1. VoxCPM  
2. CosyVoice  
3. pyttsx3  

Qwen TTS 已默认关闭（`qwen_tts.enabled: false`），需要时可改回。
