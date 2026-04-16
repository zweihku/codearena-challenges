# Zwei's CodeArena

AI 编程能力评测。clone 下来，一键启动，完成挑战。

## 快速开始

### 方式 A：Docker（推荐，零环境配置）

只需要装了 Docker Desktop，其他什么都不用。

```bash
git clone https://github.com/zweihku/codearena-challenges.git
cd codearena-challenges
./docker-start.sh
```

### 方式 B：本地 Python

需要 Python 3.10+ 和 Git。

```bash
git clone https://github.com/zweihku/codearena-challenges.git
cd codearena-challenges
./setup.sh
```

两种方式进去后操作完全一样。

## 做题流程

### 1. 启动后配置 API Key

首次进入需要配置 AI 模型（出题者会提供 API Key）：

```
Zwei's CodeArena > config
```

### 2. 输入 start 开始

```
Zwei's CodeArena > start
```

进入后会看到 Task 列表：

```
Task 列表：
  ○ Task 1   基础对话入口
  ○ Task 2   常见问题处理
  ○ Task 3   上下文连续对话
  ○ Task 4   人工转接
  ○ Task 5   会话记录与查询
  ○ Task 6   服务闭环
```

### 3. 做题

直接打字和 AI 对话，或者用命令操作文件和终端。

### 4. 完成 Task 后标记

```
[你的昵称] > /finish 1
✓ Task 1 已标记完成 (1/6)
```

### 常用命令

| 命令 | 说明 |
|------|------|
| 直接打字 | 和 AI 对话 |
| `/task` | 查看 Task 列表和完成状态 |
| `/finish N` | 标记 Task N 完成 |
| `/read 文件名` | 读取文件内容 |
| `/edit 文件名` | 让 AI 编辑文件 |
| `python xxx.py` | 直接执行命令（自动识别） |
| `git add / commit` | 直接执行 Git 命令 |
| `/ls` | 列出目录文件 |
| `/status` | 查看用时、Task 进度、对话次数 |
| `/taskmd` | 查看完整题目描述 |
| `/help` | 所有命令帮助 |
| `/quit` | 退出（结果自动上传） |

## 注意事项

- 做到哪算哪，质量比数量重要
- 所有 AI 交互会被记录，用于评测分析
- 退出后结果自动上传
- 具体题目见 `challenges/CHALLENGE.md`

## 环境要求

**Docker 模式（推荐）：** 只需 Docker Desktop + 网络连接
**本地模式：** Python 3.10+ + Git + 网络连接

## 有问题？

找出题者。
