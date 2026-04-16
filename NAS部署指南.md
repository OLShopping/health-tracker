# 飞牛 NAS Docker Compose 部署指南

> 适用：健康追踪 v2.6，仓库 [OLShopping/health-tracker](https://github.com/OLShopping/health-tracker)
> 部署端口：**4321**（外部访问），容器内 **5555**

---

## 一、基础环境确认

在飞牛 NAS 的 Web 终端（或 SSH）中执行：

```bash
# 确认 Docker 已安装
docker --version
# Docker version 2x.xx, build xxxxx

# 确认 docker-compose 已安装
docker compose version
# Docker Compose version v2.xx
```

> 💡 飞牛 NAS 安装应用 → 搜索「Docker」→ 安装官方套件即可

---

## 二、SSH 连接飞牛 NAS

### 方式 A：飞牛 Web 终端（推荐）
1. 飞牛后台 → 右上角头像 → 控制台
2. 直接在网页终端操作

### 方式 B：SSH（适合习惯命令行的人）
```bash
ssh 用户名@NAS_IP地址
# 例：ssh admin@192.168.1.100
```

---

## 三、创建部署目录

```bash
# 在 NAS 上创建项目目录（放在 /volume1/docker/ 或你喜欢的路径）
mkdir -p /volume1/docker/health-tracker
cd /volume1/docker/health-tracker
```

---

## 四、克隆代码到 NAS 本地目录

```bash
cd /volume1/docker/health-tracker

# 克隆仓库（公开仓库无需 token）
git clone https://github.com/OLShopping/health-tracker.git .

# 如果目录已存在，先清空再克隆：
# rm -rf /volume1/docker/health-tracker/*
# git clone https://github.com/OLShopping/health-tracker.git .
```

---

## 五、创建 .env 环境变量文件

> ⚠️ `.env` 文件不会被提交到 GitHub，用于存储敏感信息

```bash
cd /volume1/docker/health-tracker

# 创建 .env 文件（粘贴以下内容并保存）
cat > .env << 'EOF'
# GitHub Token（公开仓库可留空，私有仓库必填）
GITHUB_TOKEN=

# 仓库分支
BRANCH=main
EOF

# 确认文件创建成功
cat .env
```

> 💡 **如何获取 GitHub Token：**
> 1. 打开 https://github.com/settings/tokens
> 2. 点击 **Generate new token (classic)**
> 3. 勾选 `repo` 权限
> 4. 生成后复制 token，填入上面的 `GITHUB_TOKEN=你的token`

---

## 六、创建持久化目录

```bash
cd /volume1/docker/health-tracker

# 创建数据持久化目录
mkdir -p data uploads

# 设置权限（确保 Docker 能写入）
chmod 777 data uploads
```

---

## 七、启动服务

```bash
cd /volume1/docker/health-tracker

# 拉取最新代码 + 构建镜像 + 启动容器
docker compose up -d --build
```

**参数说明：**
- `-d`：后台运行
- `--build`：重新构建镜像（**每次代码更新后必须加此参数**）

---

## 八、验证部署

### 查看容器状态
```bash
docker compose ps
```

### 查看日志
```bash
docker compose logs -f
# 按 Ctrl+C 退出日志
```

### 健康检查
```bash
# 等待约 10 秒后测试
curl http://localhost:5555/api/health
# 应返回 {"status":"ok"} 或类似内容
```

---

## 九、访问应用

```
http://你的NAS_IP地址:4321
```

> 例：`http://192.168.1.100:4321`

---

## 十、后续代码更新流程

代码更新后（GitHub 有新 commit），需要先拉取本地文件，再重建容器：

```bash
cd /volume1/docker/health-tracker

# 拉取最新代码到本地
git pull

# 重建容器
docker compose up -d --build
```

---

## 十一、完整操作流程（从头开始一次性执行）

```bash
# 1. 进入部署目录（没有就创建）
mkdir -p /volume1/docker/health-tracker
cd /volume1/docker/health-tracker

# 2. 克隆代码（首次）
git clone https://github.com/OLShopping/health-tracker.git .

# 3. 创建持久化目录
mkdir -p data uploads
chmod 777 data uploads

# 4. 启动（构建镜像 + 运行容器）
docker compose up -d --build

# 6. 等待 10 秒后验证
sleep 10 && curl http://localhost:5555/api/health
```

---

## 十二、常用维护命令

```bash
# 查看容器状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 完全删除容器（保留数据）
docker compose down --remove-orphans

# 完全删除容器+镜像（清理重建）
docker compose down --rmi all
```

---

## 十三、故障排查

| 问题 | 解决方法 |
|------|---------|
| `docker: command not found` | 飞牛后台安装 Docker 套件 |
| `curl: Connection refused` | 等待 30 秒让容器启动完成 |
| 页面空白/API 报错 | 查看日志 `docker compose logs` |
| 端口 4321 被占用 | 修改 `docker-compose.yml` 中 `"4321:5555"` 改为 `"4322:5555"` |
| `docker build` 失败 | 检查网络是否通畅；镜像层缓存可能导致旧错误，加 `--no-cache` 强制重建 |
| 代码未更新 | 先执行 `git pull`，再 `docker compose up -d --build` |

---

## 十四、数据备份

所有数据存在 `./data/health.db`，定期备份：

```bash
# 备份数据库
cp /volume1/docker/health-tracker/data/health.db ~/backup/health.db.$(date +%Y%m%d)
```

