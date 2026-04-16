#!/bin/bash
# CodeArena 参赛者一键启动脚本
# 用法: ./setup.sh

set -e

# Ctrl+C 只退出 CodeArena CLI，不中断后续收集/上传流程

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
GITHUB_REPO="zweihku/codearena-challenges"

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║     Zwei's CodeArena 挑战启动    ║"
echo "  ╚══════════════════════════════════╝"
echo ""

# ============================================================
# Step 1: 检查环境
# ============================================================

echo "[1/4] 检查环境..."

# Git
if ! command -v git &>/dev/null; then
    echo "  ❌ 需要 Git。请先安装 Git。"
    exit 1
fi
echo "  ✓ Git $(git --version | cut -d' ' -f3)"

# CodeArena binary
CODEARENA_BIN="$REPO_ROOT/bin/codearena"
if [ ! -x "$CODEARENA_BIN" ]; then
    echo "  ❌ CodeArena CLI 未找到"
    echo "  请确保 bin/codearena 文件存在且有执行权限"
    exit 1
fi
echo "  ✓ CodeArena CLI v$($CODEARENA_BIN --version 2>/dev/null || echo '?')"

# ============================================================
# Step 2: 参赛者登录
# ============================================================

echo ""
echo "[2/4] 参赛者登录"
echo ""
echo "  请输入你的参赛昵称（英文字母/数字/下划线，最多20字符）"
echo ""

while true; do
    read -p "  昵称: " NICKNAME
    NICKNAME=$(echo "$NICKNAME" | tr -cd 'a-zA-Z0-9_-')
    if [ -z "$NICKNAME" ]; then
        echo "  ⚠ 昵称不能为空"
        continue
    fi
    if [ ${#NICKNAME} -gt 20 ]; then
        echo "  ⚠ 昵称太长（最多 20 字符）"
        continue
    fi
    break
done

echo "  ✓ 欢迎, $NICKNAME!"

# 检查 API key
if [ -z "$ZHIPU_API_KEY" ]; then
    echo ""
    echo "  请输入出题者提供的 API Key:"
    read -r -p "  API Key: " USER_KEY
    if [ -n "$USER_KEY" ]; then
        export ZHIPU_API_KEY="$USER_KEY"
    fi
fi

if [ -z "$ZHIPU_API_KEY" ]; then
    echo "  ❌ 必须提供 API Key 才能使用 AI 助手"
    exit 1
fi
echo "  ✓ API Key 已配置"

# ============================================================
# Step 3: 创建专属分支
# ============================================================

echo ""
echo "[3/4] 创建你的专属分支..."

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

# 保存昵称
echo "$NICKNAME" > "$REPO_ROOT/.participant"

# 记录挑战开始时间
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ============================================================
# Step 4: 启动 Zwei's CodeArena
# ============================================================

echo ""
echo "[4/4] 启动 Zwei's CodeArena..."
echo ""
echo "  ┌──────────────────────────────────────────────────┐"
echo "  │  使用指南:                                        │"
echo "  │                                                   │"
echo "  │  /task    — 查看当前挑战的任务列表               │"
echo "  │  /finish  — 完成某个任务后登记完成               │"
echo "  │                                                   │"
echo "  │  让 AI 助手帮你逐个完成 Task                     │"
echo "  │  完成后按 Ctrl+C 退出                            │"
echo "  └──────────────────────────────────────────────────┘"
echo ""

# Resize terminal window wider (50 rows x 160 cols)
printf '\e[8;50;160t' 2>/dev/null || true

# 启动 CodeArena CLI（Ctrl+C 只退出 CLI，脚本继续执行收集流程）
cd "$REPO_ROOT"
set +e
trap '' INT
"$CODEARENA_BIN" || true
trap - INT
set -e

# ============================================================
# 退出后自动收集结果并上传
# ============================================================

END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo ""
echo "  正在收集结果..."

# 复制挑战目录下的代码文件到结果目录
CHALLENGE_DIR="$REPO_ROOT/challenges"
if [ -d "$CHALLENGE_DIR" ]; then
    mkdir -p "$RESULTS_DIR/code"
    # 复制参赛者写的所有文件（排除题目文件）
    for f in "$CHALLENGE_DIR"/*; do
        fname="$(basename "$f")"
        [ -f "$f" ] || continue
        [[ "$fname" == "CHALLENGE.md" ]] && continue
        [[ "$fname" == test_* ]] && continue
        cp "$f" "$RESULTS_DIR/code/"
    done
    # 复制子目录
    for d in "$CHALLENGE_DIR"/*/; do
        dname="$(basename "$d")"
        [[ "$dname" == "starter" ]] && continue
        [[ "$dname" == "__pycache__" ]] && continue
        cp -r "$d" "$RESULTS_DIR/code/" 2>/dev/null || true
    done

    # 导出 commit 历史（空文件 = 用户未做版本管理，本身也是评测信号）
    cd "$REPO_ROOT"
    COMMIT_DATA=$(git log --pretty=format:'{"hash":"%h","date":"%ai","message":"%s"}' -- challenges/ 2>/dev/null)
    if [ -n "$COMMIT_DATA" ]; then
        echo "$COMMIT_DATA" | sed 's/$/,/' | sed '1s/^/[/' | sed '$ s/,$/]/' > "$RESULTS_DIR/commits.json"
        COMMIT_COUNT=$(echo "$COMMIT_DATA" | wc -l | tr -d ' ')
        echo "  ✓ Git 历史: ${COMMIT_COUNT} 条 commit"
    else
        echo '{"git_managed": false, "note": "参赛者未使用 git 管理代码"}' > "$RESULTS_DIR/commits.json"
        echo "  ⚠ 未检测到 git commit（将记录此信息）"
    fi
fi

# ---- 收集任务完成记录 (challenge-progress.json) ----
PROGRESS_FILE="$HOME/.local/share/codearena/challenge-progress.json"
if [ -f "$PROGRESS_FILE" ]; then
    cp "$PROGRESS_FILE" "$RESULTS_DIR/challenge-progress.json"
    echo "  ✓ 任务完成记录已收集"
fi

# ---- 收集 AI 对话日志 (opencode session DB + logs) ----
OPENCODE_DATA="$HOME/.local/share/opencode"
if [ -d "$OPENCODE_DATA" ]; then
    mkdir -p "$RESULTS_DIR/ai-logs"

    # 复制 SQLite 数据库（包含完整对话历史）
    for db in "$OPENCODE_DATA"/opencode*.db; do
        [ -f "$db" ] && cp "$db" "$RESULTS_DIR/ai-logs/" 2>/dev/null || true
    done

    # 复制本次运行的文本日志
    if [ -d "$OPENCODE_DATA/log" ]; then
        mkdir -p "$RESULTS_DIR/ai-logs/log"
        cp "$OPENCODE_DATA/log/"* "$RESULTS_DIR/ai-logs/log/" 2>/dev/null || true
    fi
    echo "  ✓ AI 对话日志已收集"

    # 导出 AI 对话为评测可读的 JSONL 格式
    for db in "$RESULTS_DIR/ai-logs"/opencode*.db; do
        [ -f "$db" ] || continue
        DBNAME="$(basename "$db" .db)"
        sqlite3 "$db" "
            SELECT data FROM message ORDER BY time_created
        " > "$RESULTS_DIR/ai-conversation-${DBNAME}.jsonl" 2>/dev/null || true
    done
    echo "  ✓ AI 对话 JSONL 已导出"
fi

# ---- 导出 agent/mode 切换时间线 ----
if command -v sqlite3 &>/dev/null; then
    for db in "$RESULTS_DIR/ai-logs"/opencode*.db; do
        [ -f "$db" ] || continue
        DBNAME="$(basename "$db" .db)"
        sqlite3 "$db" "
            SELECT json_object(
                'timestamp', datetime(time_created/1000, 'unixepoch'),
                'role', json_extract(data,'$.role'),
                'agent', json_extract(data,'$.agent'),
                'mode', json_extract(data,'$.mode'),
                'model', json_extract(data,'$.modelID')
            )
            FROM message ORDER BY time_created
        " | sed 's/$/,/' | sed '1s/^/[/' | sed '$ s/,$/]/' \
          > "$RESULTS_DIR/agent-timeline-${DBNAME}.json" 2>/dev/null
    done
    echo "  ✓ Agent/Mode 切换时间线已收集"
fi

# ---- 汇总 token 消耗 ----
if command -v sqlite3 &>/dev/null; then
    for db in "$RESULTS_DIR/ai-logs"/opencode*.db; do
        [ -f "$db" ] || continue
        DBNAME="$(basename "$db" .db)"
        sqlite3 "$db" "
            SELECT json_object(
                'total_input', SUM(json_extract(data,'$.tokens.input')),
                'total_output', SUM(json_extract(data,'$.tokens.output')),
                'total_reasoning', SUM(json_extract(data,'$.tokens.reasoning')),
                'total_cache_read', SUM(json_extract(data,'$.tokens.cache.read')),
                'total_cache_write', SUM(json_extract(data,'$.tokens.cache.write')),
                'total_cost', ROUND(SUM(json_extract(data,'$.cost')), 4),
                'message_count', COUNT(*)
            )
            FROM message
            WHERE json_extract(data,'$.role') = 'assistant'
        " > "$RESULTS_DIR/token-usage-${DBNAME}.json" 2>/dev/null
    done
    echo "  ✓ Token 消耗统计已收集"
fi

# ---- 写入时间戳元数据 ----
cat > "$RESULTS_DIR/metadata.json" <<METAEOF
{
  "participant": "$NICKNAME",
  "branch": "$BRANCH",
  "startTime": "$START_TIME",
  "endTime": "$END_TIME",
  "durationSeconds": $(( $(date +%s) - $(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$START_TIME" +%s 2>/dev/null || echo 0) ))
}
METAEOF
echo "  ✓ 时间戳元数据已写入"

echo "  ✓ 结果已收集到 $RESULTS_DIR/"

# Git 提交并推送
echo "  正在上传结果..."
cd "$REPO_ROOT"
git add "results/$NICKNAME/" challenges/ 2>/dev/null || true
git commit -m "results: $NICKNAME submission" 2>/dev/null || true

# 尝试 push
if git push origin "$BRANCH" 2>/dev/null; then
    echo "  ✓ 结果已上传到 GitHub ($BRANCH)"
else
    echo "  ⚠ 自动上传失败（可能没有 push 权限）"
    echo "  请手动运行: git push origin $BRANCH"
fi

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║     感谢参与！结果已保存。       ║"
echo "  ╚══════════════════════════════════╝"
echo ""
echo "  你的结果文件在: $RESULTS_DIR/"
ls "$RESULTS_DIR/" 2>/dev/null || echo "  (空)"
