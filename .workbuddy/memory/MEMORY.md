# 项目长期记忆：health-tracker

## 项目性质
个人健康追踪 Web 应用，由 WorkBuddy 辅助开发（截至 2026-03-27）。

## 技术栈
- **后端**：Python 3.11 + Flask 3.0.3，SQLite WAL 模式，单文件 app/main.py
- **前端**：纯原生 HTML5/CSS3/JS，单文件 app/templates/index.html，Chart.js 4.4.3（CDN）
- **部署**：Docker + docker-compose，端口 5555，支持飞牛 NAS

## 数据库结构
5张表：medicines、dose_schedules、med_logs、bp_records、bowel_records

## 核心功能
1. 服药打卡（按时段分组：早/午/晚/自定义，打卡自动扣库存）
2. 库存管理（剩余天数计算，三色预警）
3. 服药日历（月视图，full/partial/missed 状态）
4. 血压（近30天 Chart.js 折线趋势图，含收缩压峰/谷值）+ 心率（独立图表）
5. 大便记录（手动时间 + 布里斯托1-7型形态 + 备注 + 统计间隔）
6. 数据备份恢复（JSON全量 + CSV分表）

## 已知问题/改进点
- ~~无用户认证（局域网裸奔）~~ 2026-03-29 添加密码认证后因页面白屏回滚，暂未启用
- ~~图片更换后旧文件未清理~~ ✅ 已修复（2026-03-29）
- ~~血压图表仅取每日均值~~ ✅ 已修复，现展示均值+峰/谷值（2026-03-29）
- SECRET_KEY 默认值需生产环境修改

## 开发历史（已修复 Bug）
- 2026-03-26：服药页改为按时段分组（非药品名称分组）
- 2026-03-26：追加剩余天数显示及颜色预警
- 2026-03-27：confirmTake/deleteMedLog 改 await，解决库存刷新滞后
- 2026-03-27：medicine_id 类型修复（Number()转换）
- 2026-03-27：daily_dose=0 时返回 999 天
- 2026-03-29：upload_medicine_photo/delete_medicine 增加旧文件清理逻辑
- 2026-03-29：renderBPChart 升级，同日多条记录展示均值+峰/谷值虚线，tooltip 显示测量次数
- 2026-03-29：血压图表移除心率数据集，新增独立心率图表（renderPulseChart）
- 2026-03-29：大便记录增加手动时间、备注、布里斯托形态分类（stool_type字段，含数据库迁移）
- 2026-03-29：添加访问密码认证（环境变量 AUTH_PASSWORD，前端登录遮罩，API Token 验证）
- 2026-03-29：密码功能回滚（前端因 api() 函数丢失导致白屏，已恢复无密码版本）

## 部署命令
```bash
# 本地开发
DB_PATH=./data/health.db python app/main.py

# Docker（推荐）
docker compose up -d
# 访问 http://宿主机IP:5555
```
