# Mutsuki (Sakura)

PySide6 桌面桌宠：Live2D 立绘、对话 Agent、TTS、歌词叠加与托盘控制。

## 环境

- Windows 10+
- Python 3.12（推荐使用仓库内 `runtime/`，或自行安装依赖）

## 安装与运行

```powershell
.\install.bat
.\start.bat
```

或直接：

```powershell
.\runtime\python.exe main.py
```

## 本地资源（不入库）

克隆后需自行准备：

- `runtime/`：内置 Python 与依赖（或 `pip install -r requirements.txt`）
- `characters/`：角色包
- `立绘/`：Live2D 模型资源
- `data/models/`：Whisper / GPT-SoVITS 等模型权重
- `data/config/api.yaml` 等私密配置（见 `data/config/` 示例）

## License

MIT
