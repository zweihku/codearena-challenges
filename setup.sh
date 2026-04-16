#!/bin/bash
# CodeArena 参赛者一键启动脚本
# 用法: ./setup.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
GITHUB_REPO="zweihku/codearena-challenges"

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║       CodeArena 挑战启动         ║"
echo "  ╚══════════════════════════════════╝"
echo ""

# ============================================================
# Step 1: 检查环境
# ============================================================

echo "[1/5] 检查环境..."

# Python
if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 Python 3.10+。请先安装 Python。"
    exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✓ Python $PY_VERSION"

# Git
if ! command -v git &>/dev/null; then
    echo "❌ 需要 Git。请先安装 Git。"
    exit 1
fi
echo "  ✓ Git $(git --version | cut -d' ' -f3)"

# ============================================================
# Step 2: 安装依赖
# ============================================================

echo "[2/5] 安装依赖..."
pip install -q openai rich prompt_toolkit requests httpx 2>/dev/null
echo "  ✓ 依赖已安装"

# ============================================================
# Step 3: 输入昵称
# ============================================================

echo ""
echo "[3/5] 参赛者登录"
echo ""
echo "  请输入你的参赛昵称（英文，用于标记你的所有记录）"
echo ""

while true; do
    read -p "  昵称: " NICKNAME
    NICKNAME=$(echo "$NICKNAME" | tr -cd 'a-zA-Z0-9_-')
    if [ -z "$NICKNAME" ]; then
        echo "  ⚠ 昵称不能为空，只支持英文字母/数字/下划线"
        continue
    fi
    if [ ${#NICKNAME} -gt 20 ]; then
        echo "  ⚠ 昵称太长（最多 20 字符）"
        continue
    fi
    break
done

echo "  ✓ 欢迎, $NICKNAME!"
echo ""

# ============================================================
# Step 4: 创建专属分支
# ============================================================

echo "[4/5] 创建你的专属分支..."

BRANCH="participant/$NICKNAME"

# 检查分支是否已存在（本地或远程）
if git show-ref --verify --quiet "refs/heads/$BRANCH" 2>/dev/null; then
    echo "  分支 $BRANCH 已存在，切换过去..."
    git checkout "$BRANCH"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH" 2>/dev/null; then
    echo "  远程分支已存在，拉取并切换..."
    git checkout -b "$BRANCH" "origin/$BRANCH"
else
    git checkout -b "$BRANCH"
    echo "  ✓ 创建新分支 $BRANCH"
fi

# 创建结果目录
RESULTS_DIR="$REPO_ROOT/results/$NICKNAME"
mkdir -p "$RESULTS_DIR"

# ============================================================
# Step 5: 启动 CodeArena CLI
# ============================================================

echo "[5/5] 启动 CodeArena CLI..."
echo ""
echo "  ┌────────────────────────────────────────────┐"
echo "  │  提示:                                      │"
echo "  │  - 输入 start 开始挑战                      │"
echo "  │  - 每完成一个 task 输入 /commit \"taskN: done\"│"
echo "  │  - 输入 /quit 退出（结果自动上传）          │"
echo "  └────────────────────────────────────────────┘"
echo ""

# 检查 API key
if [ -z "$ZHIPU_API_KEY" ]; then
    echo "  ⚠ 未设置 ZHIPU_API_KEY 环境变量"
    echo "  请输入智谱 API Key（或按回车跳过，在 CLI 中配置）:"
    read -p "  API Key: " USER_KEY
    if [ -n "$USER_KEY" ]; then
        export ZHIPU_API_KEY="$USER_KEY"
    fi
fi

# 保存昵称到文件，供 arena.py 读取（跳过登录）
echo "$NICKNAME" > "$REPO_ROOT/.participant"

# 启动 CLI
cd "$REPO_ROOT"
python3 arena-cli/arena.py \
    --challenges-dir "$REPO_ROOT" \
    --log-dir "$RESULTS_DIR" \
    --participant "$NICKNAME"

# ============================================================
# 退出后自动收集结果并上传
# ============================================================

echo ""
echo "  正在收集结果..."

# 复制挑战目录下的代码文件到结果目录
CHALLENGE_DIR="$REPO_ROOT/challenges"
if [ -d "$CHALLENGE_DIR" ]; then
    mkdir -p "$RESULTS_DIR/code"
    # 复制参赛者写的所有文件（排除测试和题目文件）
    for f in "$CHALLENGE_DIR"/*; do
        fname="$(basename "$f")"
        [ -f "$f" ] || continue
        # 排除出题者的文件
        [[ "$fname" == "CHALLENGE.md" ]] && continue
        [[ "$fname" == test_* ]] && continue
        cp "$f" "$RESULTS_DIR/code/"
    done
    # 复制子目录（starter 等）
    for d in "$CHALLENGE_DIR"/*/; do
        dname="$(basename "$d")"
        [[ "$dname" == "starter" ]] && continue
        [[ "$dname" == "__pycache__" ]] && continue
        cp -r "$d" "$RESULTS_DIR/code/" 2>/dev/null || true
    done

    # 导出 commit 历史
    cd "$REPO_ROOT"
    git log --pretty=format:'{"hash":"%h","date":"%ai","message":"%s"}' -- challenges/ > "$RESULTS_DIR/commits.json" 2>/dev/null || true

    # 导出测试结果
    cd "$CHALLENGE_DIR"
    python3 -m pytest test_challenge.py -v --tb=short 2>&1 > "$RESULTS_DIR/test_results.txt" || true
    cd "$REPO_ROOT"

    # AI 交互日志已在 results 目录下（arena-cli 直接写到 --log-dir）
    # 确认日志存在
    if ls "$RESULTS_DIR"/*.jsonl 1>/dev/null 2>&1; then
        echo "  ✓ AI 交互日志已保存"
    fi
fi

echo "  ✓ 结果已收集到 $RESULTS_DIR/"

# Git 提交并推送
echo "  正在上传结果..."
cd "$REPO_ROOT"
git add "results/$NICKNAME/" 2>/dev/null || true
git commit -m "results: $NICKNAME submission" 2>/dev/null || true

# 尝试 push（可能因为没有远程权限失败，不是大问题）
if git push origin "$BRANCH" 2>/dev/null; then
    echo "  ✓ 结果已上传到 GitHub ($BRANCH)"
else
    echo "  ⚠ 自动上传失败（可能没有 push 权限）"
    echo "  请手动运行: git push origin $BRANCH"
    echo "  或把 results/$NICKNAME/ 文件夹发给出题者"
fi

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║     感谢参与！结果已保存。       ║"
echo "  ╚══════════════════════════════════╝"
echo ""
echo "  你的结果文件在: $RESULTS_DIR/"
ls "$RESULTS_DIR/"
