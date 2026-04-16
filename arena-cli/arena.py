#!/usr/bin/env python3
"""
CodeArena CLI — 内部测试用 AI 编程助手

一个带完整交互日志的 AI 编程助手，用于 hackathon 评测。
参赛者用它和 AI 对话、读写文件、执行命令，所有交互被记录。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich import box
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.history import FileHistory
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("运行: pip install openai rich prompt_toolkit")
    sys.exit(1)

console = Console()

# ============================================================
# 配置
# ============================================================

PROVIDERS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "default_model": "glm-5.1",
        "env_key": "ZHIPU_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
}

CHALLENGES = {
    "A": {
        "name": "天气服务",
        "difficulty": "★★☆ → ★★★★",
        "dir": "challenges/a-weather-cli",
        "desc": "CLI 天气查询工具，6 个递进 task：基础查询→健壮性→JSON→缓存→并发→完善",
    },
    "B": {
        "name": "笔记搜索引擎",
        "difficulty": "★★★ → ★★★★",
        "dir": "challenges/b-note-search",
        "desc": "Markdown 语义搜索，6 个递进 task：扫描→关键词→TF-IDF→索引→语义搜索→完善",
    },
    "C": {
        "name": "API 限流中间件",
        "difficulty": "★★★ → ★★★★★",
        "dir": "challenges/c-rate-limiter",
        "desc": "生产级限流器，6 个递进 task：计数器→状态→线程安全→滑动窗口→令牌桶→中间件",
    },
}


def detect_challenges(base_dir: Path) -> dict:
    """自动检测挑战目录结构，支持两种模式：
    1. 多挑战模式：challenges/a-weather-cli/, challenges/b-note-search/ 等
    2. 单挑战模式：challenges/ 直接就是挑战目录（repo 部署模式）
    """
    # 先检查单挑战模式（challenges/ 下直接有 CHALLENGE.md）
    single = base_dir / "challenges" / "CHALLENGE.md"
    if single.exists():
        # 从 CHALLENGE.md 第一行提取名称
        first_line = single.read_text(encoding="utf-8").split("\n")[0]
        name = first_line.replace("#", "").strip()
        name = name.split("：")[0].split("（")[0].strip() if name else "当期挑战"
        return {
            "A": {
                "name": name,
                "difficulty": "",
                "dir": "challenges",
                "desc": "当期挑战",
            }
        }

    # 多挑战模式：检测已有的子目录
    detected = {}
    for key, ch in CHALLENGES.items():
        ch_dir = base_dir / ch["dir"]
        if (ch_dir / "CHALLENGE.md").exists():
            detected[key] = ch

    return detected if detected else CHALLENGES

SYSTEM_PROMPT = """你是 CodeArena AI 编程助手，帮助参赛者完成 hackathon 编程挑战。

你的行为准则：
1. 帮助参赛者理解题目、调试代码、给出建议
2. 可以直接写代码，但鼓励参赛者理解每一步
3. 当参赛者问你要完整答案时，先问他思路，再补充
4. 回复简洁，代码直接给，不要过多解释

你可以使用以下命令帮参赛者操作：
- 读取文件内容并分析
- 给出代码修改建议
- 解释错误信息

当前挑战：{challenge_name}
工作目录：{work_dir}
"""

# ============================================================
# 日志记录
# ============================================================

class InteractionLogger:
    def __init__(self, log_dir: str, participant: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{participant}.jsonl"
        self.participant = participant
        self.seq = 0
        self.session_id = f"session_{int(time.time())}"

    def log(self, event_type: str, model: str = "", request_msgs=None,
            response_text: str = "", tool_name: str = "", tool_input: str = "",
            tool_output: str = "", latency_ms: int = 0, tokens: dict = None):
        self.seq += 1
        entry = {
            "seq": self.seq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "participant": self.participant,
            "event_type": event_type,  # chat / tool_read / tool_edit / tool_run / model_switch
            "model": model,
            "request": {
                "messages": request_msgs or [],
            } if event_type == "chat" else None,
            "response": response_text if event_type == "chat" else None,
            "tool": {
                "name": tool_name,
                "input": tool_input[:2000],  # 截断大输出
                "output": tool_output[:2000],
            } if tool_name else None,
            "latency_ms": latency_ms,
            "tokens": tokens,
        }
        # 去掉 None 值
        entry = {k: v for k, v in entry.items() if v is not None}

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_stats(self) -> dict:
        if not self.log_file.exists():
            return {"total": 0, "chats": 0, "tools": 0}
        lines = self.log_file.read_text().strip().split("\n")
        chats = sum(1 for l in lines if '"chat"' in l)
        tools = sum(1 for l in lines if '"tool_' in l)
        return {"total": len(lines), "chats": chats, "tools": tools}


# ============================================================
# AI 对话引擎
# ============================================================

class ArenaEngine:
    def __init__(self, provider: str, model: str, api_key: str, work_dir: str,
                 challenge: dict, logger: InteractionLogger):
        config = PROVIDERS[provider]
        self.client = OpenAI(api_key=api_key, base_url=config["base_url"])
        self.model = model
        self.provider = provider
        self.work_dir = Path(work_dir)
        self.challenge = challenge
        self.logger = logger
        self.messages = []

        # 初始化 system prompt
        system = SYSTEM_PROMPT.format(
            challenge_name=challenge["name"],
            work_dir=str(self.work_dir),
        )
        # 加载挑战题目
        challenge_file = self.work_dir / "CHALLENGE.md"
        if challenge_file.exists():
            system += f"\n\n## 挑战题目\n\n{challenge_file.read_text(encoding='utf-8')}"

        self.system_prompt = system

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        api_messages = [{"role": "system", "content": self.system_prompt}] + self.messages

        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=8192,
                temperature=0.7,
            )
        except Exception as e:
            error_msg = f"API 调用失败: {e}"
            self.messages.pop()  # 回滚
            return error_msg

        latency = int((time.time() - start) * 1000)
        text = response.choices[0].message.content or ""
        usage = response.usage

        self.messages.append({"role": "assistant", "content": text})

        # 日志
        self.logger.log(
            event_type="chat",
            model=self.model,
            request_msgs=[{"role": "user", "content": user_input}],
            response_text=text,
            latency_ms=latency,
            tokens={
                "input": usage.prompt_tokens if usage else 0,
                "output": usage.completion_tokens if usage else 0,
            },
        )

        return text

    def switch_model(self, new_model: str, new_provider: str = None):
        if new_provider and new_provider in PROVIDERS:
            config = PROVIDERS[new_provider]
            api_key = os.environ.get(config["env_key"], "")
            if api_key:
                self.client = OpenAI(api_key=api_key, base_url=config["base_url"])
                self.provider = new_provider
            else:
                return f"错误: 未设置 {config['env_key']}"
        self.model = new_model
        self.logger.log(event_type="model_switch", model=new_model)
        return f"已切换到 {new_model} ({self.provider})"


# ============================================================
# 文件/命令工具
# ============================================================

def tool_read(filepath: str, work_dir: Path, logger: InteractionLogger) -> str:
    """读取文件内容"""
    p = work_dir / filepath
    if not p.exists():
        return f"文件不存在: {filepath}"
    if not p.is_file():
        return f"不是文件: {filepath}"
    try:
        content = p.read_text(encoding="utf-8")
        logger.log(event_type="tool_read", tool_name="read",
                    tool_input=filepath, tool_output=content[:500])
        return content
    except Exception as e:
        return f"读取失败: {e}"


def tool_edit(filepath: str, content: str, work_dir: Path, logger: InteractionLogger) -> str:
    """写入文件"""
    p = work_dir / filepath
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.log(event_type="tool_edit", tool_name="edit",
                    tool_input=filepath, tool_output=f"写入 {len(content)} 字符")
        return f"已写入 {filepath} ({len(content)} 字符)"
    except Exception as e:
        return f"写入失败: {e}"


def tool_run(cmd: str, work_dir: Path, logger: InteractionLogger) -> str:
    """执行命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, cwd=str(work_dir),
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        logger.log(event_type="tool_run", tool_name="run",
                    tool_input=cmd, tool_output=output[:1000])
        return output if output.strip() else "(无输出)"
    except subprocess.TimeoutExpired:
        return "命令超时 (30秒)"
    except Exception as e:
        return f"执行失败: {e}"


def tool_ls(work_dir: Path) -> str:
    """列出目录文件"""
    files = []
    for f in sorted(work_dir.iterdir()):
        if f.name.startswith("."):
            continue
        if f.is_dir():
            files.append(f"  {f.name}/")
        else:
            size = f.stat().st_size
            files.append(f"  {f.name}  ({size} bytes)")
    return "\n".join(files) if files else "(空目录)"


# ============================================================
# 主界面
# ============================================================

def show_welcome():
    """显示欢迎页"""
    title = Text()
    title.append("  ██████╗ ██████╗ ██████╗ ███████╗\n", style="bold cyan")
    title.append("  ██╔════╝██╔═══██╗██╔══██╗██╔════╝\n", style="bold cyan")
    title.append("  ██║     ██║   ██║██║  ██║█████╗  \n", style="bold cyan")
    title.append("  ██║     ██║   ██║██║  ██║██╔══╝  \n", style="bold cyan")
    title.append("  ╚██████╗╚██████╔╝██████╔╝███████╗\n", style="bold cyan")
    title.append("   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝\n", style="bold cyan")
    title.append("        A R E N A", style="bold white")

    console.print(Panel(title, border_style="cyan", padding=(1, 4)))
    console.print()

    guide = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    guide.add_column(style="bold cyan", width=18)
    guide.add_column()
    guide.add_row("start", "开始挑战 — 登录昵称 → 选择任务 → 进入编程")
    guide.add_row("help", "查看命令帮助")
    guide.add_row("quit", "退出 CodeArena")

    console.print(Panel(guide, title="[bold]命令指南[/bold]", border_style="dim"))
    console.print()


def show_help():
    """显示详细帮助"""
    t = Table(box=box.ROUNDED, title="CodeArena 命令", title_style="bold")
    t.add_column("命令", style="cyan", width=22)
    t.add_column("说明")

    t.add_row("[bold]/ask[/bold] <问题>", "问 AI 一个问题（也可以直接打字，不加 /ask）")
    t.add_row("[bold]/read[/bold] <文件>", "读取文件内容并显示")
    t.add_row("[bold]/edit[/bold] <文件>", "让 AI 编辑文件（AI 会给出修改后的完整内容）")
    t.add_row("[bold]/run[/bold] <命令>", "执行 shell 命令（如 pytest, python weather.py 等）")
    t.add_row("[bold]/test[/bold] [taskN]", "运行当前挑战的测试（可指定 task 编号）")
    t.add_row("[bold]/ls[/bold]", "列出当前目录文件")
    t.add_row("[bold]/commit[/bold] <msg>", "git add + commit")
    t.add_row("[bold]/model[/bold] <名称>", "切换 AI 模型（如 glm-5.1, gpt-5.4）")
    t.add_row("[bold]/status[/bold]", "查看当前会话状态")
    t.add_row("[bold]/task[/bold]", "查看挑战题目")
    t.add_row("[bold]/help[/bold]", "显示本帮助")
    t.add_row("[bold]/quit[/bold]", "退出")

    console.print(t)
    console.print()
    console.print("[dim]提示: 直接输入文字就是和 AI 对话，不需要加 /ask 前缀[/dim]")


def select_challenge(challenges: dict) -> str:
    """选择挑战"""
    keys = list(challenges.keys())

    # 只有一个挑战时直接进入
    if len(keys) == 1:
        ch = challenges[keys[0]]
        console.print(f"[bold cyan]当期挑战: {ch['name']}[/bold cyan]")
        return keys[0]

    t = Table(box=box.ROUNDED, title="选择挑战", title_style="bold")
    t.add_column("编号", style="bold cyan", width=4)
    t.add_column("名称", width=16)
    t.add_column("难度", width=14)
    t.add_column("说明")

    for key, ch in challenges.items():
        t.add_row(key, ch["name"], ch.get("difficulty", ""), ch.get("desc", ""))

    console.print(t)
    console.print()

    valid = [k.lower() for k in keys] + [k.upper() for k in keys]
    while True:
        choice = Prompt.ask("选择挑战", choices=valid)
        return choice.upper()


def login() -> str:
    """登录昵称"""
    console.print()
    console.print("[bold]请输入你的参赛昵称[/bold]")
    console.print("[dim]（用于标记你的所有交互记录，建议用英文）[/dim]")
    console.print()

    while True:
        name = Prompt.ask("昵称")
        name = name.strip()
        if not name:
            console.print("[red]昵称不能为空[/red]")
            continue
        if len(name) > 20:
            console.print("[red]昵称太长（最多 20 字符）[/red]")
            continue
        # 只允许字母数字下划线中文
        name = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
        console.print(f"[green]欢迎, {name}![/green]")
        return name


def run_session(participant: str, challenge_key: str, provider: str,
                model: str, api_key: str, base_dir: Path, log_dir: str,
                challenges: dict = None):
    """主交互循环"""
    all_challenges = challenges or detect_challenges(base_dir)
    challenge = all_challenges.get(challenge_key)
    if not challenge:
        console.print(f"[red]未找到挑战 {challenge_key}[/red]")
        return
    work_dir = base_dir / challenge["dir"]

    if not work_dir.exists():
        console.print(f"[red]挑战目录不存在: {work_dir}[/red]")
        console.print("[yellow]请确认 challenges/ 目录结构正确[/yellow]")
        return

    logger = InteractionLogger(log_dir, participant)
    engine = ArenaEngine(provider, model, api_key, str(work_dir), challenge, logger)

    # 初始化 git
    git_dir = work_dir / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=str(work_dir),
                       capture_output=True, timeout=10)
        subprocess.run(["git", "add", "-A"], cwd=str(work_dir),
                       capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "init: challenge start"],
                       cwd=str(work_dir), capture_output=True, timeout=10)

    # 显示进入挑战信息
    console.print()
    info = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    info.add_column(style="bold", width=10)
    info.add_column()
    info.add_row("参赛者", participant)
    info.add_row("挑战", f"{challenge_key}: {challenge['name']}")
    info.add_row("模型", f"{model} ({provider})")
    info.add_row("目录", str(work_dir))
    info.add_row("日志", f"{log_dir}/{participant}.jsonl")

    console.print(Panel(info, title="[bold green]挑战开始[/bold green]", border_style="green"))
    console.print()
    console.print("[dim]输入 /help 查看命令  |  直接打字和 AI 对话  |  /quit 退出[/dim]")
    console.print()

    # 输入历史
    history_file = Path(log_dir) / f".{participant}_history"
    history = FileHistory(str(history_file))

    start_time = time.time()

    while True:
        try:
            user_input = pt_prompt(
                f"[{participant}] > ",
                history=history,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        # ---- 自动检测：像命令但没加 /run ----
        SHELL_PREFIXES = (
            "pytest ", "python ", "python3 ", "pip ", "npm ", "node ",
            "cat ", "ls ", "cd ", "mkdir ", "git ", "curl ", "grep ",
        )
        if user_input.lower().startswith(SHELL_PREFIXES) and not user_input.startswith("/"):
            console.print(f"[dim]检测到命令，自动执行: {user_input}[/dim]")
            output = tool_run(user_input, work_dir, logger)
            console.print(output)
            continue

        # ---- 命令处理 ----

        if user_input in ("/quit", "/exit", "quit", "exit"):
            break

        elif user_input in ("/help", "help"):
            show_help()
            continue

        elif user_input in ("/ls", "ls"):
            console.print(tool_ls(work_dir))
            continue

        elif user_input in ("/status", "status"):
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            stats = logger.get_stats()
            console.print(f"  参赛者: {participant}")
            console.print(f"  挑战: {challenge_key} - {challenge['name']}")
            console.print(f"  模型: {engine.model} ({engine.provider})")
            console.print(f"  用时: {mins}分{secs}秒")
            console.print(f"  AI 对话: {stats['chats']} 次")
            console.print(f"  工具调用: {stats['tools']} 次")
            continue

        elif user_input in ("/task", "task"):
            challenge_file = work_dir / "CHALLENGE.md"
            if challenge_file.exists():
                content = challenge_file.read_text(encoding="utf-8")
                console.print(Markdown(content))
            else:
                console.print("[yellow]未找到 CHALLENGE.md[/yellow]")
            continue

        elif user_input.startswith("/read "):
            filepath = user_input[6:].strip()
            content = tool_read(filepath, work_dir, logger)
            if len(content) > 3000:
                console.print(Syntax(content[:3000], "python", theme="monokai"))
                console.print(f"[dim]... 截断 (共 {len(content)} 字符)[/dim]")
            elif filepath.endswith(".py"):
                console.print(Syntax(content, "python", theme="monokai", line_numbers=True))
            elif filepath.endswith((".md", ".txt")):
                console.print(Markdown(content))
            else:
                console.print(content)
            continue

        elif user_input.startswith("/run "):
            cmd = user_input[5:].strip()
            console.print(f"[dim]$ {cmd}[/dim]")
            output = tool_run(cmd, work_dir, logger)
            console.print(output)
            continue

        elif user_input.startswith("/test"):
            parts = user_input.split()
            if len(parts) > 1 and parts[1].isdigit():
                task_num = parts[1]
                cmd = f"python -m pytest test_challenge.py -v -k task{task_num}"
            else:
                cmd = "python -m pytest test_challenge.py -v"
            console.print(f"[dim]$ {cmd}[/dim]")
            output = tool_run(cmd, work_dir, logger)
            console.print(output)
            continue

        elif user_input.startswith("/commit"):
            msg = user_input[7:].strip() or "update"
            console.print(f"[dim]$ git add -A && git commit -m \"{msg}\"[/dim]")
            tool_run("git add -A", work_dir, logger)
            output = tool_run(f'git commit -m "{msg}"', work_dir, logger)
            console.print(output)
            continue

        elif user_input.startswith("/model "):
            parts = user_input[7:].strip().split()
            new_model = parts[0]
            new_provider = parts[1] if len(parts) > 1 else None
            result = engine.switch_model(new_model, new_provider)
            console.print(f"[cyan]{result}[/cyan]")
            continue

        elif user_input.startswith("/edit "):
            # 把文件内容发给 AI，让 AI 修改
            filepath = user_input[6:].strip()
            content = tool_read(filepath, work_dir, logger)
            if content.startswith("文件不存在") or content.startswith("读取失败"):
                # 新文件
                ai_prompt = f"请为 {filepath} 生成代码。直接给出完整文件内容，用 ```python 代码块包裹。"
            else:
                ai_prompt = f"以下是 {filepath} 的当前内容：\n\n```\n{content}\n```\n\n请修改这个文件。给出修改后的完整文件内容，用 ```python 代码块包裹。"

            console.print(f"[dim]正在让 AI 编辑 {filepath}...[/dim]")
            response = engine.chat(ai_prompt)

            # 从 AI 回复中提取代码块
            code_match = re.search(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
            if code_match:
                new_content = code_match.group(1)
                if Confirm.ask(f"AI 生成了 {len(new_content)} 字符的代码，写入 {filepath}?"):
                    result = tool_edit(filepath, new_content, work_dir, logger)
                    console.print(f"[green]{result}[/green]")
                else:
                    console.print("[yellow]已取消[/yellow]")
            else:
                console.print(Markdown(response))
            continue

        elif user_input.startswith("/"):
            console.print(f"[red]未知命令: {user_input.split()[0]}[/red]")
            console.print("[dim]输入 /help 查看可用命令[/dim]")
            continue

        # ---- 普通对话 ----
        with console.status("[cyan]AI 思考中...[/cyan]"):
            response = engine.chat(user_input)

        console.print()
        console.print(Markdown(response))
        console.print()

    # ---- 退出 ----
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)
    stats = logger.get_stats()

    console.print()
    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    summary.add_column(style="bold", width=12)
    summary.add_column()
    summary.add_row("用时", f"{mins}分{secs}秒")
    summary.add_row("AI 对话", f"{stats['chats']} 次")
    summary.add_row("工具调用", f"{stats['tools']} 次")
    summary.add_row("日志", str(logger.log_file))

    console.print(Panel(summary, title="[bold]会话结束[/bold]", border_style="cyan"))


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="CodeArena CLI")
    parser.add_argument("--provider", default="zhipu", choices=list(PROVIDERS.keys()))
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--challenges-dir", default=None,
                        help="challenges 所在目录（默认自动检测）")
    parser.add_argument("--log-dir", default="./arena-logs")
    args = parser.parse_args()

    # 检测 challenges 目录
    base_dir = Path(args.challenges_dir) if args.challenges_dir else None
    if base_dir is None:
        candidates = [
            Path(__file__).parent.parent,           # repo 根目录（setup.sh 调用时）
            Path.cwd(),                             # 当前目录
            Path(__file__).parent.parent / "mini-hackathon",  # 开发时
            Path.cwd() / "mini-hackathon",
        ]
        for c in candidates:
            # 支持两种结构：challenges/CHALLENGE.md 或 challenges/a-weather-cli/CHALLENGE.md
            if (c / "challenges" / "CHALLENGE.md").exists():
                base_dir = c
                break
            if (c / "challenges" / "a-weather-cli" / "CHALLENGE.md").exists():
                base_dir = c
                break
    if base_dir is None:
        console.print("[red]找不到 challenges 目录[/red]")
        console.print("[yellow]请在项目根目录下运行，或用 --challenges-dir 指定[/yellow]")
        sys.exit(1)

    # 检测可用挑战
    available_challenges = detect_challenges(base_dir)

    # API key
    provider_config = PROVIDERS[args.provider]
    api_key = args.api_key or os.environ.get(provider_config["env_key"], "")
    if not api_key:
        console.print(f"[red]需要设置 {provider_config['env_key']} 环境变量[/red]")
        sys.exit(1)

    model = args.model or provider_config["default_model"]

    # ---- 主界面循环 ----
    show_welcome()

    while True:
        try:
            cmd = Prompt.ask("[bold cyan]CodeArena[/bold cyan]", default="").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ("start", "s"):
            participant = login()
            challenge_key = select_challenge(available_challenges)
            run_session(participant, challenge_key, args.provider, model,
                       api_key, base_dir, args.log_dir)
            # 回到主界面
            console.print()
            show_welcome()

        elif cmd in ("help", "h"):
            show_help()

        elif cmd in ("quit", "q", "exit"):
            console.print("[dim]再见![/dim]")
            break

        elif cmd:
            console.print(f"[yellow]未知命令: {cmd}[/yellow]")
            console.print("[dim]输入 start 开始，help 查看帮助，quit 退出[/dim]")


if __name__ == "__main__":
    main()
