#!/usr/bin/env python3
"""
CodeArena 评测脚本
对单个参赛者的提交进行 5 维评测，输出结构化报告。

用法：
    python evaluate.py \
        --challenge ../challenges/a-weather-cli/CHALLENGE.md \
        --code-dir ./data/participant1/code/ \
        --commits ./data/participant1/commits.json \
        --test-results ./data/participant1/test_results.txt \
        --ai-logs ./data/participant1/ai_logs.jsonl \
        --output ./data/participant1/report.json

环境变量：
    ZHIPU_API_KEY - 智谱 GLM API key（默认使用智谱）
    OPENAI_API_KEY - 如果想用 OpenAI 兼容接口

支持的 LLM 后端（通过 --provider 切换）：
    zhipu   - 智谱 GLM-4-Flash（默认）
    openai  - OpenAI 或任何兼容接口
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("需要安装 openai SDK: pip install openai")
    sys.exit(1)


# LLM 后端配置（均兼容 OpenAI SDK 格式）
LLM_PROVIDERS = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-5.1",
        "env_key": "ZHIPU_API_KEY",
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "env_key": "MINIMAX_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "env_key": "DASHSCOPE_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "custom": {
        "base_url": "",  # 需要通过 --base-url 传入
        "model": "",     # 需要通过 --model 传入
        "env_key": "LLM_API_KEY",
    },
}


def read_file(path: str) -> str:
    """读取文件，不存在返回空字符串"""
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def read_code_dir(code_dir: str, max_files: int = 20, max_chars: int = 50000) -> str:
    """读取代码目录下的关键文件"""
    code_dir = Path(code_dir)
    if not code_dir.exists():
        return "(代码目录不存在)"

    files = []
    total_chars = 0
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".md"}
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".next"}

    for f in sorted(code_dir.rglob("*")):
        if f.is_dir():
            continue
        if any(skip in f.parts for skip in skip_dirs):
            continue
        if f.suffix not in extensions:
            continue
        if len(files) >= max_files:
            break

        content = read_file(str(f))
        if total_chars + len(content) > max_chars:
            content = content[:max_chars - total_chars] + "\n...(截断)"

        rel_path = f.relative_to(code_dir)
        files.append(f"### {rel_path}\n```\n{content}\n```")
        total_chars += len(content)

        if total_chars >= max_chars:
            break

    return "\n\n".join(files) if files else "(未找到代码文件)"


EVAL_PROMPT = """你是一个资深技术评测专家。根据以下信息，对参赛者的 Hackathon 表现进行 6 维度评测。

评分标准：
- 1-3 分：未完成/质量差
- 4-5 分：基本完成但有明显问题
- 6-7 分：完成且质量尚可
- 8-9 分：高质量完成，有亮点
- 10 分：卓越，超出预期

## 挑战题目

{challenge}

## 参赛者提交的代码

{code}

## Git Commit 历史

{commits}

## 自动化测试结果

{test_results}

## AI 工具交互日志（CodeArena 完整记录）

{ai_logs}

## 评测重点说明

1. **AI 日志是最核心的数据源。** 每条日志包含参赛者发给 AI 的完整 prompt、AI 的完整回复、使用的模型、耗时。通过分析对话内容可以判断：参赛者是在思考后提出精确问题，还是盲目让 AI 生成全部代码。
2. **Git commit 历史反映工程习惯。** 如果 commit 历史为空或只有初始 commit，说明参赛者没有版本管理意识，这本身就是一个负面信号，应在 engineering_habits_score 中扣分。有清晰的分 task commit 说明参赛者有工程纪律。
3. **没有数据也是数据。** 如果某项数据缺失（没有 commit、没有测试结果、没有 AI 日志），不要跳过评分，而是根据缺失本身评分。例如：没有 commit = 工程习惯差，没有跑测试 = 质量意识不足。

请严格按以下 JSON 格式输出（不要包含 markdown 代码块标记）：

{{
  "result_score": {{"score": <1-10>, "reason": "<一句话，基于测试通过率和代码功能完整度>"}},
  "engineering_quality_score": {{"score": <1-10>, "reason": "<一句话，代码结构、命名、错误处理、可读性>"}},
  "engineering_habits_score": {{"score": <1-10>, "reason": "<一句话，评估工程习惯：commit 频率和质量（每个 task 一个 commit = 好, 零 commit = 差）、是否跑了测试、是否写 README、是否有类型注解。没有 commit 历史最高给 4 分>"}},
  "tool_usage_score": {{"score": <1-10>, "reason": "<一句话，分析 AI 对话日志：prompt 是否精确、是否分步迭代、是否验证 AI 输出、是否盲目接受。如无日志则标注'推测'>"}},
  "problem_decomposition_score": {{"score": <1-10>, "reason": "<一句话，是否按 task 递进推进、是否在 AI 对话中先拆解再实现>"}},
  "efficiency_score": {{"score": <1-10>, "reason": "<一句话，完成了几个 task、时间分配是否合理>"}},
  "composite_score": <六项加权平均（权重：结果 20%、代码质量 20%、工程习惯 15%、AI 运用 20%、问题拆解 15%、效率 10%），保留一位小数>,
  "key_moments": [
    {{"time": "<从 AI 日志时间戳或 commit 时间推算>", "description": "<做了什么>", "significance": "<为什么重要>"}}
  ],
  "highlights": "<一段话总结亮点，引用具体的 AI 对话内容或代码细节>",
  "improvements": "<一段话总结提升空间，具体指出缺失的工程实践>",
  "data_completeness": {{
    "has_test_results": <true/false>,
    "has_ai_logs": <true/false>,
    "has_commit_history": <true/false>,
    "commit_count": <数字，0 表示没有有意义的 commit>,
    "ai_interaction_count": <数字，AI 对话总次数>,
    "notes": "<数据完整性说明，指出哪些维度的评分因数据缺失而降低>"
  }}
}}
"""


def get_llm_client(provider: str, api_key: str = None, base_url: str = None) -> tuple:
    """返回 (OpenAI client, model_name)"""
    config = LLM_PROVIDERS.get(provider)
    if not config:
        print(f"未知 provider: {provider}，支持: {list(LLM_PROVIDERS.keys())}")
        sys.exit(1)

    key = api_key or os.environ.get(config["env_key"], "")
    if not key:
        print(f"需要设置 {config['env_key']} 环境变量，或用 --api-key 参数传入")
        sys.exit(1)

    url = base_url or config["base_url"]
    if provider == "custom" and not url:
        print("custom provider 需要 --base-url 参数")
        sys.exit(1)

    client = OpenAI(api_key=key, base_url=url)
    return client, config["model"]


def evaluate(challenge: str, code: str, commits: str, test_results: str,
             ai_logs: str, provider: str = "zhipu", api_key: str = None,
             model: str = None, base_url: str = None) -> dict:
    """调用 LLM 进行评测"""
    client, default_model = get_llm_client(provider, api_key, base_url)
    use_model = model or default_model

    prompt = EVAL_PROMPT.format(
        challenge=challenge or "(未提供题目)",
        code=code or "(未提供代码)",
        commits=commits or "(无 commit 历史)",
        test_results=test_results or "(未运行测试)",
        ai_logs=ai_logs or "(无 AI 交互日志)",
    )

    print(f"  使用模型: {use_model} ({provider})")

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=use_model,
                max_tokens=16384,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "你是一个技术评测专家。请严格按要求输出 JSON 格式，不要包含 markdown 代码块标记。直接输出 JSON，不要有任何前缀文字。"},
                    {"role": "user", "content": prompt},
                ],
            )

            text = response.choices[0].message.content or ""
            text = text.strip()

            # 去掉可能的 markdown 代码块
            if text.startswith("```"):
                first_newline = text.index("\n") if "\n" in text else 3
                text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:text.rfind("```")]
            text = text.strip()

            # 直接解析
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # 尝试提取 JSON 部分
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
                raise

        except (json.JSONDecodeError, Exception) as e:
            if attempt < max_retries:
                print(f"  ⚠ 第 {attempt+1} 次尝试失败 ({e}), 重试...")
                continue
            print(f"  ✗ {max_retries+1} 次尝试均失败")
            print(f"  原始输出前 800 字: {text[:800]}")
            raise ValueError(f"无法解析 LLM 输出为 JSON: {e}")


def format_report(report: dict, participant: str) -> str:
    """格式化为可读报告"""
    c = report["composite_score"]
    lines = [
        f"{'='*50}",
        f"  参赛者: {participant}",
        f"  综合得分: {c} / 10",
        f"{'='*50}",
        "",
    ]

    dimensions = [
        ("result_score", "结果正确性"),
        ("engineering_quality_score", "工程质量  "),
        ("engineering_habits_score", "工程习惯  "),
        ("tool_usage_score", "AI工具运用 "),
        ("problem_decomposition_score", "问题拆解  "),
        ("efficiency_score", "时间效率  "),
    ]

    for key, label in dimensions:
        score = report[key]["score"]
        reason = report[key]["reason"]
        bar = "█" * score + "░" * (10 - score)
        lines.append(f"  {label} {bar}  {score:>4.1f}  {reason}")

    lines.append("")
    lines.append("  关键时刻：")
    for moment in report.get("key_moments", []):
        lines.append(f"  {moment['time']}  {moment['description']}")

    lines.append("")
    lines.append(f"  亮点：{report.get('highlights', '')}")
    lines.append(f"  提升：{report.get('improvements', '')}")

    dq = report.get("data_completeness", report.get("data_quality", {}))
    if dq:
        flags = []
        if not dq.get("has_ai_logs"):
            flags.append("AI日志缺失(工具运用为推测)")
        if not dq.get("has_test_results"):
            flags.append("未运行测试")
        if not dq.get("has_commit_history"):
            flags.append("无 commit 记录(工程习惯扣分)")
        commit_n = dq.get("commit_count", "?")
        ai_n = dq.get("ai_interaction_count", "?")
        lines.append(f"\n  数据: {commit_n} commits | {ai_n} AI 对话")
        if flags:
            lines.append(f"  ⚠ {'; '.join(flags)}")

    lines.append(f"\n{'='*50}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="CodeArena 评测")
    parser.add_argument("--challenge", required=True, help="题目文件路径")
    parser.add_argument("--code-dir", required=True, help="参赛者代码目录")
    parser.add_argument("--commits", default="", help="commit 历史 JSON 文件")
    parser.add_argument("--test-results", default="", help="测试结果文件")
    parser.add_argument("--ai-logs", default="", help="AI 交互日志 JSONL 文件")
    parser.add_argument("--output", default="report.json", help="报告输出路径")
    parser.add_argument("--participant", default="unknown", help="参赛者名称")
    parser.add_argument("--provider", default="zhipu", choices=list(LLM_PROVIDERS.keys()),
                        help="LLM 后端 (默认: zhipu)")
    parser.add_argument("--api-key", default=None, help="API key（也可用环境变量）")
    parser.add_argument("--model", default=None, help="覆盖默认模型名")
    parser.add_argument("--base-url", default=None, help="自定义 API base URL（用于 custom provider）")
    args = parser.parse_args()

    print(f"评测 {args.participant}...")

    challenge = read_file(args.challenge)
    code = read_code_dir(args.code_dir)
    commits = read_file(args.commits)
    test_results = read_file(args.test_results)
    ai_logs = read_file(args.ai_logs)

    report = evaluate(challenge, code, commits, test_results, ai_logs,
                      provider=args.provider, api_key=args.api_key,
                      model=args.model, base_url=args.base_url)

    # 保存 JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"JSON 报告已保存到 {output_path}")

    # 打印可读报告
    print("\n" + format_report(report, args.participant))


if __name__ == "__main__":
    main()
