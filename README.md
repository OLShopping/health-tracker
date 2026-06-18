# 🏥 个人健康追踪

一款轻量级个人健康追踪 Web 应用，支持部署在飞牛 NAS 或任意 Docker 环境。

## ✨ 功能

| 模块 | 功能 |
|------|------|
| 💊 服药记录 | 早/中/晚分时段打卡，支持 1/4、1/3、1/2、整片等精细剂量 |
| 📋 服药计划 | 按药品分组展示当前方案：时段+剂量+总剂量+剩余药量；停用药品置底分隔 |
| ⚡ 一键服药 | 每个时段一键批量记录，可自定义服药时间 |
| 📦 库存管理 | 实时计算剩余天数，3天橙色警告 / 0天红色闪烁；停用药品置底显示 |
| 📷 药品照片 | 上传药品图片和备注 |
| 📅 服药日历 | 月视图，绿色=全服、黄色=部分、红色=漏服，点击查看详情和编辑记录 |
| ❤️ 血压心率 | 记录血压/脉率，显示近30天趋势图 |
| 🚽 大便记录 | 一键记录，统计距上次间隔和平均间隔 |
| 💾 数据备份 | JSON 完整备份 + CSV 导出，支持数据恢复 |

## 🚀 快速部署

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目
git clone https://github.com/OLShopping/health-tracker.git health-tracker
cd health-tracker

# 启动（首次构建会自动安装依赖）
docker compose up -d --build

# 访问
open http://localhost:4321
```

### 方式二：飞牛 NAS

1. 在飞牛 NAS 的 Docker 管理界面，选择"从 Compose 部署"
2. 上传本项目目录，或直接粘贴 `docker-compose.yml` 内容
3. 启动容器

### 🔄 NAS 更新代码（版本号驱动重建）

> 每次新代码推送到 GitHub 后：

1. 在 NAS 上拉取最新代码：
   ```bash
   cd /path/to/health-tracker
   git pull
   ```
2. 修改 `docker-compose.yml` 中的 `APP_VERSION` 为新版本号（如 `2.9`）
3. 重新构建并启动：
   ```bash
   docker compose up -d --build
   ```

> **原理**：Dockerfile 通过 `ARG APP_VERSION` 参数控制缓存，版本号变化时会强制重新执行 COPY 及后续步骤，确保使用最新代码。数据（`data/` 和 `uploads/`）不受影响。

### 方式三：本地直接运行（开发用）

```bash
pip install flask flask-cors pillow python-dateutil
python app/main.py
# 访问 http://localhost:5555
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
├── Dockerfile               # COPY 本地文件构建，ARG APP_VERSION 驱动缓存失效
├── docker-compose.yml       # build.args 含 APP_VERSION
├── requirements.txt
└── README.md
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_PATH` | `/data/health.db` | 数据库文件路径 |
| `SECRET_KEY` | `change-me-in-production` | Flask 密钥（生产环境请修改） |
| `PORT` | `5555` | 服务端口 |
| `TZ` | `Asia/Shanghai` | 时区 |

## 🔒 数据安全

- 数据库为单个 SQLite 文件，存储在 `data/health.db`
- 建议定期使用内置备份功能导出 JSON 或 CSV
- Docker 部署时数据持久化在宿主机 `./data` 和 `./uploads` 目录
- 重建容器不会影响已有数据

## 📱 支持设备

- 手机（H5，底部 Tab 导航）
- 电脑（顶部导航栏 + 底部 Tab 双导航）
- 平板（自适应布局）

---

## 📝 更新日志

### v2.8（2026-06-18）
- 📋 新增「服药计划」页面，按药品分组展示时段+剂量标签+总剂量+剩余药量
- 📋 停用药品（日用量=0）置底灰色区域，渐变横线分隔
- 💊 「一键全服」改名为「一键服药」，支持自定义服药时间
- ❤️ 血压历史记录：心形符号改为「脉率：X」文字，字体与血压数值一致
- 🔖 标题栏自动显示版本号
- 🐳 Dockerfile 加 `ARG APP_VERSION` 实现版本号驱动缓存失效
- 🚀 电脑端导航新增「📋 计划」按钮

### v2.7（2026-06-18）
- ⚡ 每个时段新增「一键服药」按钮，点击后确认弹窗列出所有未服药品及剂量，一次性批量记录
- 支持自定义服药时间（默认当前时间）

### v2.6（2026-04-16）
- 📅 日历页：选中日期显示明显高亮（蓝色粗边框+放大+加深背景）
- 📅 日历页：底部服药详情按药物分组，列出时段（早/中/晚），颜色区分全服✅/部分⚠️/未服❌

### v2.5（2026-04-07）
- 🚽 大便记录：统计卡新增「约X天」显示，将小时数换算为天数（最小单位0.5天），便于直观理解排便间隔

### v2.4（2026-04-06）
- 💊 今日服药：库存卡片新增「预计X月X日耗尽」显示
- 📷 药品照片：支持上传药品图片，配合打卡识别

### v2.3（2026-04-05）
- 📊 血压趋势图：新增点击交互，点击折线点显示详细数据

### v2.0（2026-04-04）
- 🗓️ 服药日历：月视图，按日聚合服药记录
