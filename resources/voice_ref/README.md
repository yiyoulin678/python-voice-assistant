# 声音克隆参考音频



## 方式一：GUI 里现场克隆（推荐）



1. 打开小音 GUI  

2. 点 **「选择克隆音频」**  

3. 选你的 wav/mp3（建议 **3～10 秒**、安静、单人清晰人声）  

4. **VoxCPM1.5 + x_vector_only**：可不填台词；若效果不佳可填写与录音一致的文字到 `voxcpm.prompt_text`



当前为 **VoxCPM 克隆模式**，模型常驻显存，**不用每句话重新加载**。



## 方式二：无参考音频（声音设计）



在 `config/ai_settings.json` 中设：



```json

"voxcpm": { "mode": "design", "voice_design_prefix": "温柔甜美的年轻女声，亲切自然" }

```



## 方式三：手动放文件



复制为 `reference.wav`。



## 配置说明（`config/ai_settings.json` → `voxcpm`）



| 字段 | 说明 |

|------|------|

| `model_id` | `openbmb/VoxCPM1.5`（快）或 `openbmb/VoxCPM2`（更强） |

| `mode` | `clone` / `design` |

| `x_vector_only_mode` | `true` = 仅参考音频（VoxCPM2 最佳） |

| `voice_design_prefix` | design 模式下的声线描述 |



详见 `docs/SETUP_VOXCPM.md`。

