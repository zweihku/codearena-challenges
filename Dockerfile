FROM python:3.12-slim

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY arena-cli/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制项目文件
WORKDIR /arena
COPY . .

# Git 配置（容器内需要）
RUN git config --global user.name "arena-participant" && \
    git config --global user.email "participant@codearena.local" && \
    git config --global init.defaultBranch main

# 入口
ENTRYPOINT ["python3", "arena-cli/arena.py", "--challenges-dir", "/arena", "--log-dir", "/arena/results"]
