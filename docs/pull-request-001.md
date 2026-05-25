# Pull Request #1

**Title:** `feat(cli): 添加 devices 子命令列出录音设备`

**Closes:** #1

---

## Summary

- 在 `audio_io` 中新增 `list_input_devices()` 与 `format_devices_text()`
- CLI 新增 `devices` 子命令
- README 补充「查看麦克风/输入设备」说明

## 变更说明

解决 Issue #1：用户可确认系统默认输入与可用录音设备，便于无麦克风/多设备环境排错。

## 如何测试

```bash
cd VoiceAssistant
python run_demo.py devices
```

## AI 使用说明（实验要求）

本 PR 在 Cursor 中使用 AI 辅助完成设备枚举 API 设计、CLI 集成与文档更新；人工核对 sounddevice API 与本地运行结果。

## Checklist

- [x] 代码 > 10 行
- [x] 本地可运行
- [x] 更新 README
