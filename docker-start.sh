#!/bin/bash
# Docker 一键启动（不需要本地装 Python/Git）
# 用法: ./docker-start.sh

set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║    Zwei's CodeArena (Docker 模式)    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "❌ 需要先安装 Docker Desktop"
    echo ""
    echo "   macOS:   brew install --cask docker"
    echo "   Windows: https://docs.docker.com/desktop/install/windows-install/"
    echo "   Linux:   https://docs.docker.com/engine/install/"
    echo ""
    exit 1
fi

# 检查 Docker 是否在运行
if ! docker info &>/dev/null 2>&1; then
    echo "❌ Docker 没有运行，请先启动 Docker Desktop"
    exit 1
fi

echo "[1/2] 构建环境（首次约 1 分钟，之后秒启）..."
docker build -t zwei-codearena . -q

echo "[2/2] 启动 Zwei's CodeArena..."
echo ""

# 挂载当前目录，这样参赛者的代码和日志能持久化到本地
docker run -it --rm \
    -v "$(pwd)/challenges:/arena/challenges" \
    -v "$(pwd)/results:/arena/results" \
    zwei-codearena

echo ""
echo "结果保存在 results/ 目录下"
