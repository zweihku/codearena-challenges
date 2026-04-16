# Zwei's CodeArena

AI 编程能力评测平台。参赛者在 AI 编程助手的辅助下完成编程挑战，全程记录并评测。

## 快速开始

```bash
git clone https://github.com/zweihku/codearena-challenges.git
cd codearena-challenges
bash setup.sh
```

启动后依次完成：
1. 输入参赛昵称
2. 输入出题者提供的 API Key
3. 自动创建专属分支并进入 CodeArena TUI

## 做题流程

进入 TUI 后，首页显示挑战主题和任务列表。

1. **阅读题目** — 打开 `challenges/CHALLENGE.md` 了解任务要求
2. **和 AI 对话** — 直接打字向 AI 助手提出需求，让它帮你写代码
3. **查看任务** — 输入 `/task` 查看任务列表
4. **登记完成** — 完成一个 Task 后输入 `/finish 序号` 登记（如 `/finish 1`）
5. **版本管理** — 建议每完成一个 Task 用 `git commit` 提交（这是评分项）
6. **退出** — `Ctrl+C` 退出，结果自动收集并上传

## 命令速查

| 命令 | 说明 |
|------|------|
| 直接打字 | 和 AI 助手对话 |
| `/task` | 查看任务列表 |
| `/finish N` | 登记 Task N 完成 |
| `/status` | 查看系统状态 |
| `/help` | 查看帮助 |
| `Ctrl+C` | 退出（自动收集结果） |

## 评测维度

挑战过程中以下数据会被自动记录用于评测：

- **代码产出** — 你写的所有代码
- **Git 历史** — commit 频率、质量、是否按 Task 分步提交
- **AI 交互记录** — 你和 AI 的完整对话（prompt 质量、是否验证输出）
- **Token 消耗** — AI 资源使用量
- **模式切换** — Build/Plan 模式使用情况
- **任务完成时间** — 每个 Task 的完成时间戳
- **总耗时** — 挑战开始到退出的总时长

## 注意事项

- 做到哪算哪，质量比数量重要
- AI 助手不会帮你读题，你需要自己阅读 CHALLENGE.md
- 退出后结果自动上传到你的专属分支

## 环境要求

- Git
- 网络连接（调用 AI API）
