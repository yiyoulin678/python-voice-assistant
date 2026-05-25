# Issue #1（请在 GitHub 创建）

**Title:** `feat: 添加 CLI 命令列出系统录音设备`

**Labels:** `enhancement`, `good first issue`

---

## 问题描述

当前 `audio_io` 使用系统默认麦克风，用户无法得知正在使用哪一路输入设备。在无麦克风或虚拟声卡场景下，排错困难。

## 期望行为

- 提供 `python run_demo.py devices` 列出所有可用输入设备
- 标出系统默认输入设备
- 在 README 中补充说明

## 验收标准

- [ ] 新增子命令 `devices`
- [ ] 输出包含 index、name、channels、sample rate（如有）
- [ ] 代码变更 > 10 行
- [ ] 更新 README

## 参考

课设成员3模块 `ai/audio_io.py`、`ai/demo_cli.py`
