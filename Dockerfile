# ============================================================
# 健康追踪 - Docker 构建文件
#
# 部署说明：
#   1. 本地更新代码后，推送到 GitHub
#   2. 在 NAS 上 git pull 拉取最新代码到本地目录
#   3. 执行 docker compose up -d --build
#
# （COPY 构建阶段使用本地文件，build 时无需访问外网）
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# -------- 安装系统依赖 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -------- 复制本地代码（NAS 上 git pull 后即可用最新代码） ----------
COPY . /app/

# -------- 安装 Python 依赖 ----------
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# -------- 创建必要目录 ----------
RUN mkdir -p /data /app/static/uploads

# -------- 暴露端口 ----------
EXPOSE 5555

# -------- 启动 ----------
CMD ["python", "-u", "app/main.py"]
