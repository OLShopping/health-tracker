FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建数据目录
RUN mkdir -p /data /app/static/uploads

# 暴露端口
EXPOSE 5555

# 启动命令
CMD ["python", "-u", "app/main.py"]
