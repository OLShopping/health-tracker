# 🏥 个人健康追踪

一款轻量级个人健康追踪 Web 应用，支持部署在飞牛 NAS 或任意 Docker 环境。

## ✨ 功能

| 模块 | 功能 |
|------|------|
| 💊 服药记录 | 早/中/晚分时段打卡，支持 1/4、1/3、1/2、整片等精细剂量 |
| 📦 库存管理 | 实时计算剩余天数，3天橙色警告 / 0天红色闪烁 |
| 📷 药品照片 | 上传药品图片和备注 |
| 📅 服药日历 | 月视图，绿色=全服、黄色=部分、红色=漏服，点击查看详情 |
| ❤️ 血压心率 | 记录血压/心率，显示近30天趋势图 |
| 🚽 大便记录 | 一键记录，统计距上次间隔和平均间隔 |
| 💾 数据备份 | JSON 完整备份 + CSV 导出，支持数据恢复 |

## 🚀 快速部署

### 方式一：Docker Compose（推荐）

```bash
# 克隆/下载项目
git clone <repo-url> health-tracker
cd health-tracker

# 启动
docker compose up -d

# 访问
open http://localhost:5000
```

### 方式二：飞牛 NAS

1. 在飞牛 NAS 的 Docker 管理界面，选择"从 Compose 部署"
2. 上传本项目目录，或直接粘贴 `docker-compose.yml` 内容
3. 配置映射路径（建议将 `./data` 映射到 NAS 上的固定目录）
4. 启动容器

### 方式三：本地直接运行（开发用）

```bash
pip install flask flask-cors pillow python-dateutil
python app/main.py
# 访问 http://localhost:5000
```

## 📁 目录结构

```
health-tracker/
├── app/
│   ├── main.py              # Flask 后端
│   ├── templates/
│   │   └── index.html       # 前端单页应用
│   └── static/
│       └── uploads/         # 药品图片存储
├── data/                    # SQLite 数据库（挂载到 Docker 卷）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_PATH` | `/data/health.db` | 数据库文件路径 |
| `SECRET_KEY` | `change-me-in-production` | Flask 密钥（生产环境请修改） |
| `PORT` | `5000` | 服务端口 |
| `TZ` | `Asia/Shanghai` | 时区 |

## 🔒 数据安全

- 数据库为单个 SQLite 文件，存储在 `data/health.db`
- 建议定期使用内置备份功能导出 JSON 或 CSV
- Docker 部署时数据持久化在宿主机 `./data` 目录

## 📱 支持设备

- 手机（H5，底部 Tab 导航）
- 电脑（顶部导航栏）
- 平板（自适应布局）

---

## 📝 更新日志

### v2.5（2026-04-07）
- 🚽 大便记录：统计卡新增「约X天」显示，将小时数换算为天数（最小单位0.5天），便于直观理解排便间隔

### v2.4（2026-04-06）
- 💊 今日服药：库存卡片新增「预计X月X日耗尽」显示
- 📷 药品照片：支持上传药品图片，配合打卡识别

### v2.3（2026-04-05）
- 📊 血压趋势图：新增点击交互，点击折线点显示详细数据

### v2.0（2026-04-04）
- 🗓️ 服药日历：月视图，按日聚合服药记录
