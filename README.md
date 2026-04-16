# Zwei's CodeArena

AI 编程能力评测平台。clone 下来，一键启动，完成挑战。

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

启动后你会看到 CodeArena CLI 界面：

```
  ██████╗ ██████╗ ██████╗ ███████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██║     ██║   ██║██║  ██║█████╗
  ██║     ██║   ██║██║  ██║██╔══╝
  ╚██████╗╚██████╔╝██████╔╝███████╗
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
        A R E N A

CodeArena > start
```

输入 `start` 后选择挑战，开始做题。

### 常用操作

| 操作 | 方式 |
|------|------|
| 和 AI 对话 | 直接打字 |
| 读文件 | `/read weather.py` |
| 让 AI 编辑文件 | `/edit weather.py` |
| 跑命令 | 直接输入 `python weather.py` 或 `pytest test_challenge.py` |
| 跑单个 task 测试 | `/test 1` |
| 提交代码 | `/commit "task1: done"` |
| 查看挑战题目 | `/task` |
| 退出 | `/quit` |

### 重要规则

1. **每完成一个 Task，commit 一次**：`/commit "task1: done"`
2. **做到哪算哪**，质量比数量重要
3. **所有 AI 交互自动记录**，用于评测分析
4. 退出后结果自动上传

## 挑战说明

每个挑战有 6 个递进式 Task，2 小时总时间：

```
Task 1-2  ★★☆    基础功能，人人能做
Task 3-4  ★★★    工程能力分界线
Task 5-6  ★★★★   高手区
```

具体题目见 `challenges/CHALLENGE.md`。

## 环境要求

**Docker 模式（推荐）：** 只需 Docker Desktop + 网络连接
**本地模式：** Python 3.10+ + Git + 网络连接

## 有问题？

找出题者。
