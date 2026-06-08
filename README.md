# Mutsuki

基于 **PySide6 + Live2D** 的 AI 桌面桌宠，面向《Python 程序设计》AI 方向课程实践。  
桌宠本体负责 **GUI、Agent 核心、语音与 Live2D 交互**；用户体系与 SQLite 后台由队友模块对接。

---

## 功能概览

### 桌宠体验

| 能力 | 说明 |
|------|------|
| Live2D 立绘 | 透明无边框窗口、点击/闲置换表情、动作播放、口型与字幕 |
| 语音交互 | GPT-SoVITS TTS、Whisper STT（可选）、流式播放与打断 |
| 主动关怀 | 空闲时主动搭话，可附带屏幕上下文 |
| 托盘与设置 | 系统托盘、多标签设置页（角色 / API / TTS / AI / MCP 等） |
| 聊天历史 | 按角色保存对话与语音片段 |

### AI 核心（课设重点）

| 能力 | 模块 | 说明 |
|------|------|------|
| Agent 对话 | `app/agent/runtime.py` | 多步工具调用、分段 JSON 回复、角色人设 |
| 文档 RAG | `app/rag/knowledge_base.py` | 索引 `data/knowledge/*.md\|txt`，工具 `knowledge_search` |
| 轻量网页搜索 | `app/agent/builtin_tools.py` | 内置 `web_search` / `fetch_url`（DuckDuckGo Lite，无需浏览器） |
| 长期记忆 | `app/agent/memory.py` | mem0 向量记忆，`memory_search/remember/forget` |
| 记忆整理 | `app/agent/memory_curator.py` | 多轮后后台归纳记忆 |
| 输出校验 | `app/llm/reply_validator.py` | 结构化回复解析、失败重试与修复打点 |
| 运行指标 | `app/ai/metrics.py` | 写入 `data/metrics/ai_events.jsonl` 与 `data/logs/ai.log` |
| 统计可视化 | `app/ui/ai_metrics_charts.py` | 设置 → AI → 统计图（Matplotlib） |
| 自动纪要 | `app/ai/session_summary.py` | 对话结束后写入 `data/notes/{角色id}-纪要.txt` |
| 屏幕理解 | `app/agent/screen_observation.py` | `observe_screen` 视觉摘要 |
| 主动感知 | `app/agent/proactive_care.py` | 定时检查 + 可选屏幕批次上下文 |

### 工具与扩展

| 能力 | 说明 |
|------|------|
| 内置工具 | 待办、提醒、笔记、时间、媒体键、音乐搜索页等 |
| MCP | Windows 桌面控制、Playwright 浏览器（可选）、网页搜索 MCP |
| 插件 | `plugins/` 目录 + `data/config/plugins.yaml`（含 Playwright 插件示例） |
| NapCat / QQ | OneBot v11 反向 WebSocket，桌宠作服务端（对齐 AstrBot 接入方式） |

### 课设能力对照

**本仓库已覆盖（AI 侧）：**

- GUI（PySide6）
- 网络（LLM API、网页搜索、NapCat、MCP）
- AI 核心（Agent + RAG + 记忆 + 校验 + 指标 + 可视化）
- 进阶：Matplotlib 统计图、logging 指标、QThread 后台任务（纪要 / 记忆整理 / 对话）

**待队友接入：**

- 登录 / 注册 / 改密、管理员权限
- SQLite 用户表、AI 任务表 CRUD、管理后台

---

## 项目结构

```
Mutsuki/
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
├── requirements-stt.txt      # 语音输入（Whisper）可选依赖
├── requirements-live2d.txt # Live2D 可选依赖
├── install.bat / start.bat # Windows 安装与启动
├── scripts/                # macOS / Linux 安装与启动脚本
│
├── app/                    # 应用主代码
│   ├── agent/              # Agent 运行时、工具、记忆、MCP
│   │   ├── runtime.py      # 对话决策与工具循环
│   │   ├── builtin_tools.py# 内置工具注册（含 web_search）
│   │   ├── memory.py       # 长期记忆
│   │   ├── proactive_care.py
│   │   └── mcp/            # MCP 桥接与网页搜索服务
│   ├── ai/                 # 课设 AI 增强
│   │   ├── metrics.py      # 运行事件记录
│   │   ├── stats.py        # 指标汇总
│   │   ├── chart_series.py # 统计图数据聚合
│   │   └── session_summary.py
│   ├── rag/                # 文档知识库 RAG
│   ├── llm/                # API 客户端、回复解析、提示词、校验
│   ├── voice/              # TTS / STT / 播放控制
│   ├── ui/                 # 桌宠窗口、Live2D、设置、AI 面板
│   ├── config/             # 配置加载与持久化（YAML）
│   ├── core/               # 启动引导、聊天流水线、插件管理
│   ├── storage/            # 聊天历史、视觉观察、音频
│   ├── platforms/napcat/   # QQ / NapCat 桥接
│   ├── plugins/            # 插件发现与管理
│   ├── media/              # 歌词、媒体键、正在播放检测
│   └── live2d/             # Live2D 运行时封装
│
├── data/                   # 运行时数据（部分不入库）
│   ├── config/             # api.yaml、system_config.yaml、mcp.yaml 等
│   ├── knowledge/          # RAG 文档（可放课设说明等 .md）
│   ├── metrics/            # ai_events.jsonl
│   ├── logs/               # ai.log
│   ├── notes/              # 台词笔记、自动纪要
│   └── models/             # Whisper / GPT-SoVITS 权重（本地）
│
├── plugins/                # 可安装插件（如 playwright_browser）
├── sdk/                    # 插件 SDK（PluginBase、工具注册）
├── tests/                  # 单元 / 集成 / UI 测试
├── tools/mcp/              # 第三方 MCP Server（Windows、Playwright）
├── third_party/mem0/       # 记忆子系统 vendored 代码
├── characters/             # 角色包（本地，不入库）
└── 立绘/                   # Live2D 模型资源（本地，不入库）
```

---

## 环境要求

- **系统**：Windows 10+（主要开发与演示环境；`scripts/` 提供 macOS / Linux 启动脚本）
- **Python**：3.12（推荐仓库内 `runtime/`，或自行 `pip install -r requirements.txt`）
- **可选**：GPT-SoVITS 服务、Whisper 模型、NapCat + QQ 客户端

---

## 安装与运行

```powershell
.\install.bat
.\start.bat
```

或直接：

```powershell
.\runtime\python.exe main.py
```

首次运行前在 **设置** 中配置 LLM API（`data/config/api.yaml`）。  
语音、MCP、NapCat 等可在设置页按需开启。

---

## 配置说明

| 路径 | 用途 |
|------|------|
| `data/config/api.yaml` | LLM / TTS API（私密，不入库） |
| `data/config/system_config.yaml` | 桌宠 UI、主动关怀、AI 功能开关等 |
| `data/config/characters.yaml` | 当前角色 ID |
| `data/config/mcp.yaml` | MCP Server 列表 |
| `data/config/plugins.yaml` | 插件入口 |
| `data/knowledge/` | RAG 知识库文档 |

**设置 → AI** 标签页提供：

- 知识库检索与重建索引
- 运行指标表格
- Matplotlib 统计图
- 自动纪要开关
- 打开知识库 / 指标 / 纪要目录

---

## 演示建议（答辩）

1. 桌宠对话（语音或文字）
2. 问知识库：「课设基础必做有哪些」（RAG）
3. 问实时信息：「搜一下 xxx」（`web_search`）
4. 设置 → AI → 统计图（Matplotlib）
5. 对话结束后查看 `data/notes/` 自动纪要

---

## 测试

```powershell
.\runtime\python.exe -m pytest tests/unit -q
```

---

## 本地资源（不入库）

克隆后需自行准备：

| 资源 | 说明 |
|------|------|
| `runtime/` | 内置 Python 与依赖 |
| `characters/` | 角色包 |
| `立绘/` | Live2D 模型 |
| `data/models/` | Whisper、GPT-SoVITS 等权重 |
| `data/config/api.yaml` | API 密钥等私密配置 |

---

## 参考项目

实现上借鉴了同类开源项目的思路：

- **Alife**：Live2D 动作指令、主动陪伴、视觉与记忆体验
- **AstrBot**：Agent 工具/MCP、知识库、QQ 反向 WebSocket 接入

---

## License

MIT
