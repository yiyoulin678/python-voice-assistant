# 第三方模型仓库（不提交到 Git）

## CosyVoice

```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git CosyVoice
```

路径：`third_party/CosyVoice/`  
详见 `docs/SETUP_LLM_TTS.md`。

## VoxCPM（默认 TTS）

```powershell
git clone --depth 1 https://github.com/OpenBMB/VoxCPM.git VoxCPM
# 若 GitHub 失败，可试镜像：
# git clone --depth 1 https://gitclone.com/github.com/OpenBMB/VoxCPM.git VoxCPM
```

安装依赖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_voxcpm.ps1
```

路径：`third_party/VoxCPM/`  
详见 `docs/SETUP_VOXCPM.md`。
