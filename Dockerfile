# ============================================================
# 构建参数：
#   GITHUB_TOKEN : GitHub 个人访问令牌（私有仓库需要，公开仓库可省略）
#   BRANCH       : 要构建的分支，默认为 main
#
# 用法示例（无 token，克隆 main 分支）：
#   docker build -t health-tracker .
#
# 带 token 克隆私有仓库：
#   docker build \
#     --build-arg GITHUB_TOKEN=ghp_xxx \
#     --build-arg BRANCH=main \
#     -t health-tracker .
# ============================================================

FROM python:3.11-slim

ARG GITHUB_TOKEN=""
ARG BRANCH=main

WORKDIR /app

# -------- 安装系统依赖 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# -------- 克隆代码（每次构建总是拉取最新） ----------
# 私有仓库：使用 token 拼接 URL
# 公开仓库：直接用 HTTPS URL
RUN if [ -n "$GITHUB_TOKEN" ]; then \
    git clone https://${GITHUB_TOKEN}@github.com/OLShopping/health-tracker.git /app; \
else \
    git clone https://github.com/OLShopping/health-tracker.git /app; \
    fi \
    && cd /app \
    && git fetch origin ${BRANCH} \
    && git checkout ${BRANCH}

# -------- 安装 Python 依赖 ----------
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# -------- 创建必要目录 ----------
RUN mkdir -p /data /app/static/uploads

# -------- 暴露端口 ----------
EXPOSE 5555

# -------- 启动 ----------
CMD ["python", "-u", "app/main.py"]
