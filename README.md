# CodeArena 编程挑战

AI 编程能力评测平台。clone 下来，一键启动，完成挑战。

## 快速开始

```bash
git clone https://github.com/zweihku/codearena-challenges.git
cd codearena-challenges
./setup.sh
```

`setup.sh` 会自动完成：
1. 安装 Python 依赖
2. 让你输入参赛昵称
3. 创建你的专属分支
4. 启动 CodeArena CLI

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

- Python 3.10+
- Git
- 网络连接（调用 AI API）

## 有问题？

找出题者。
