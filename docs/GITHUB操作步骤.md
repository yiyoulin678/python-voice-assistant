# GitHub 推送、Issue、PR 操作步骤

仓库：https://github.com/Mut5uki/python-voice-assistant

**已完成（2026-05-20）：**

| 项 | 链接 |
|----|------|
| Issue #1 | https://github.com/Mut5uki/python-voice-assistant/issues/1 |
| PR #2（已合并） | https://github.com/Mut5uki/python-voice-assistant/pull/2 |
| 仓库 | https://github.com/Mut5uki/python-voice-assistant |

---

## 1. 推送代码（需能访问 GitHub）

在 `VoiceAssistant` 目录打开终端：

```powershell
cd "d:\C++Project\python语音课设\VoiceAssistant"

# 若尚未拉取远程 .gitignore
git pull origin main --allow-unrelated-histories

# 推送
git push -u origin main
git push -u origin feature/list-audio-devices
```

或双击 **`push_to_github.bat`**。

首次推送需登录 GitHub（HTTPS 用户名 + Personal Access Token 作为密码）。

---

## 2. 创建 Issue

打开：https://github.com/Mut5uki/python-voice-assistant/issues/new

- **Title:** `feat: 添加 CLI 命令列出系统录音设备`
- **Body:** 复制 `docs/issue-001-list-audio-devices.md` 中 Issue 正文
- 提交后记下 Issue 编号（一般为 **#1**）

---

## 3. 创建 Pull Request

打开（推送 feature 分支后）：

https://github.com/Mut5uki/python-voice-assistant/compare/main...feature/list-audio-devices?expand=1

- **Title:** `feat(cli): add devices command to list input audio devices`
- **Description:** 复制 `docs/pull-request-001.md`，将 `Closes: #1` 改为实际 Issue 号
- 创建 PR 后点击 **Merge pull request** 合并到 `main`

---

## 4. 实验报告

编辑并提交：`docs/实验报告-实验1-开源贡献.md`

- 填写姓名、学号
- 附上 Issue / PR / `python run_demo.py devices` 截图
- 按课程云平台模板誊写或导出 PDF

---

## 5. 实验要求自检

- [x] 使用 Git
- [x] 有 Issue
- [x] 改动 > 10 行（`devices` 功能）
- [x] 有 PR
- [x] 使用 AI（Cursor）辅助开发 — 在报告中说明

截止日期：**2026/05/27 23:59:59**
