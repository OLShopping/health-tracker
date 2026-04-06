#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人健康追踪 Web 应用 - 后端主程序
"""

import os
import json
import sqlite3
import csv
import io
import base64
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ── 配置 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR.parent / "data" / "health.db"))
UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR / "static"), template_folder=str(BASE_DIR / "templates"))
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
CORS(app)


# ── 数据库初始化 ────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
        -- 药品表
        CREATE TABLE IF NOT EXISTS medicines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            unit        TEXT DEFAULT '片',
            stock       REAL DEFAULT 0,
            low_stock   REAL DEFAULT 3,
            daily_dose  REAL DEFAULT 1,
            photo       TEXT,
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 服药时段配置表（早/中/晚/自定义）
        CREATE TABLE IF NOT EXISTS dose_schedules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            period      TEXT NOT NULL,   -- morning/noon/evening/custom
            label       TEXT NOT NULL,   -- 早/中/晚/自定义名称
            dose        REAL NOT NULL,   -- 剂量（片数）
            enabled     INTEGER DEFAULT 1,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
        );

        -- 服药记录表
        CREATE TABLE IF NOT EXISTS med_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            schedule_id INTEGER,
            taken_at    TEXT NOT NULL,   -- 实际服药时间 ISO8601
            date        TEXT NOT NULL,   -- YYYY-MM-DD
            period      TEXT,            -- morning/noon/evening/custom
            dose        REAL NOT NULL,
            note        TEXT,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
        );

        -- 血压心率表
        CREATE TABLE IF NOT EXISTS bp_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL,
            date        TEXT NOT NULL,
            systolic    INTEGER NOT NULL,   -- 收缩压
            diastolic   INTEGER NOT NULL,   -- 舒张压
            pulse       INTEGER,            -- 心率
            note        TEXT
        );

        -- 大便记录表
        CREATE TABLE IF NOT EXISTS bowel_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            date        TEXT NOT NULL,
            shape       INTEGER,
            note        TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_med_logs_date ON med_logs(date);
        CREATE INDEX IF NOT EXISTS idx_med_logs_medicine ON med_logs(medicine_id);
        CREATE INDEX IF NOT EXISTS idx_bp_date ON bp_records(date);
        CREATE INDEX IF NOT EXISTS idx_bowel_date ON bowel_records(date);
        """)
        # 迁移：为已有数据库添加 shape 列（忽略报错）
        try:
            conn.execute("ALTER TABLE bowel_records ADD COLUMN shape INTEGER")
        except sqlite3.OperationalError:
            pass  # 列已存在
    print(f"[DB] 数据库初始化完成: {DB_PATH}")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── 工具函数 ────────────────────────────────────────────────────────────
def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ── 健康检查 ────────────────────────────────────────────────────────────
@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


# ═══════════════════════════════════════════════════════════════════════
# 药品管理 API
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/medicines", methods=["GET"])
def get_medicines():
    with get_db() as conn:
        meds = rows_to_list(conn.execute("SELECT * FROM medicines ORDER BY id").fetchall())
        for m in meds:
            # 计算剩余天数
            daily = m.get("daily_dose") or 0
            if daily > 0:
                m["days_left"] = round(m["stock"] / daily, 1)
            else:
                m["days_left"] = 999
            # 获取时段配置
            m["schedules"] = rows_to_list(
                conn.execute("SELECT * FROM dose_schedules WHERE medicine_id=? AND enabled=1 ORDER BY id", (m["id"],)).fetchall()
            )
    return jsonify(meds)


@app.route("/api/medicines", methods=["POST"])
def add_medicine():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "药品名称不能为空"}), 400

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO medicines (name, unit, stock, low_stock, daily_dose, notes) VALUES (?,?,?,?,?,?)",
            (name, data.get("unit", "片"), data.get("stock", 0),
             data.get("low_stock", 3), data.get("daily_dose", 1), data.get("notes", ""))
        )
        med_id = cur.lastrowid

        # 插入默认时段
        schedules = data.get("schedules", [])
        for s in schedules:
            conn.execute(
                "INSERT INTO dose_schedules (medicine_id, period, label, dose, enabled) VALUES (?,?,?,?,?)",
                (med_id, s["period"], s["label"], s["dose"], s.get("enabled", 1))
            )
    return jsonify({"id": med_id, "message": "添加成功"}), 201


@app.route("/api/medicines/<int:med_id>", methods=["PUT"])
def update_medicine(med_id):
    data = request.get_json()
    with get_db() as conn:
        conn.execute(
            """UPDATE medicines SET name=?, unit=?, stock=?, low_stock=?, daily_dose=?, notes=?,
               updated_at=datetime('now','localtime') WHERE id=?""",
            (data["name"], data.get("unit", "片"), data.get("stock", 0),
             data.get("low_stock", 3), data.get("daily_dose", 1),
             data.get("notes", ""), med_id)
        )
        # 更新时段
        if "schedules" in data:
            conn.execute("DELETE FROM dose_schedules WHERE medicine_id=?", (med_id,))
            for s in data["schedules"]:
                conn.execute(
                    "INSERT INTO dose_schedules (medicine_id, period, label, dose, enabled) VALUES (?,?,?,?,?)",
                    (med_id, s["period"], s["label"], s["dose"], s.get("enabled", 1))
                )
    return jsonify({"message": "更新成功"})


@app.route("/api/medicines/<int:med_id>", methods=["DELETE"])
def delete_medicine(med_id):
    with get_db() as conn:
        conn.execute("DELETE FROM medicines WHERE id=?", (med_id,))
    return jsonify({"message": "删除成功"})


@app.route("/api/medicines/<int:med_id>/photo", methods=["POST"])
def upload_medicine_photo(med_id):
    if "photo" not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    f = request.files["photo"]
    if f.filename == "" or not allowed_file(f.filename):
        return jsonify({"error": "不支持的文件格式"}), 400

    ext = f.filename.rsplit(".", 1)[1].lower()
    filename = f"med_{med_id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(save_path)

    with get_db() as conn:
        conn.execute("UPDATE medicines SET photo=? WHERE id=?", (filename, med_id))

    return jsonify({"photo": filename, "url": f"/static/uploads/{filename}"})


@app.route("/api/medicines/<int:med_id>/stock", methods=["POST"])
def adjust_stock(med_id):
    """补充/调整库存"""
    data = request.get_json()
    amount = data.get("amount", 0)
    with get_db() as conn:
        conn.execute("UPDATE medicines SET stock=stock+?, updated_at=datetime('now','localtime') WHERE id=?",
                     (amount, med_id))
        row = conn.execute("SELECT stock FROM medicines WHERE id=?", (med_id,)).fetchone()
    return jsonify({"stock": row["stock"] if row else 0})


# ═══════════════════════════════════════════════════════════════════════
# 服药记录 API
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/med-logs", methods=["GET"])
def get_med_logs():
    date_str = request.args.get("date", date.today().isoformat())
    med_id = request.args.get("medicine_id")
    with get_db() as conn:
        if med_id:
            logs = rows_to_list(conn.execute(
                "SELECT l.*, m.name as med_name, m.unit FROM med_logs l JOIN medicines m ON l.medicine_id=m.id WHERE l.date=? AND l.medicine_id=? ORDER BY l.taken_at",
                (date_str, med_id)).fetchall())
        else:
            logs = rows_to_list(conn.execute(
                "SELECT l.*, m.name as med_name, m.unit FROM med_logs l JOIN medicines m ON l.medicine_id=m.id WHERE l.date=? ORDER BY l.taken_at",
                (date_str,)).fetchall())
    return jsonify(logs)


@app.route("/api/med-logs", methods=["POST"])
def add_med_log():
    data = request.get_json()
    med_id = data.get("medicine_id")
    dose = data.get("dose", 1)
    period = data.get("period", "")
    taken_at = data.get("taken_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    date_str = taken_at[:10]

    with get_db() as conn:
        med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
        if not med:
            return jsonify({"error": "药品不存在"}), 404

        conn.execute(
            "INSERT INTO med_logs (medicine_id, schedule_id, taken_at, date, period, dose, note) VALUES (?,?,?,?,?,?,?)",
            (med_id, data.get("schedule_id"), taken_at, date_str, period, dose, data.get("note", ""))
        )
        # 自动扣减库存
        conn.execute("UPDATE medicines SET stock=MAX(0,stock-?), updated_at=datetime('now','localtime') WHERE id=?",
                     (dose, med_id))

    return jsonify({"message": "记录成功"}), 201


@app.route("/api/med-logs/<int:log_id>", methods=["DELETE"])
def delete_med_log(log_id):
    with get_db() as conn:
        log = conn.execute("SELECT * FROM med_logs WHERE id=?", (log_id,)).fetchone()
        if log:
            # 恢复库存
            conn.execute("UPDATE medicines SET stock=stock+?, updated_at=datetime('now','localtime') WHERE id=?",
                         (log["dose"], log["medicine_id"]))
            conn.execute("DELETE FROM med_logs WHERE id=?", (log_id,))
    return jsonify({"message": "删除成功"})


@app.route("/api/med-calendar", methods=["GET"])
def get_med_calendar():
    """获取某月的服药日历数据"""
    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))

    # 当月第一天到最后一天
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    with get_db() as conn:
        # 获取所有药品的时段计划（用于判断是否漏服）
        all_meds = rows_to_list(conn.execute(
            "SELECT m.id, m.name, ds.period, ds.label FROM medicines m JOIN dose_schedules ds ON m.id=ds.medicine_id WHERE ds.enabled=1"
        ).fetchall())

        # 获取当月服药记录（按日期和药品汇总）
        logs = rows_to_list(conn.execute(
            "SELECT date, medicine_id, period, COUNT(*) as cnt FROM med_logs WHERE date>=? AND date<=? GROUP BY date, medicine_id, period",
            (first_day.isoformat(), last_day.isoformat())
        ).fetchall())

    # 按日期汇总
    log_map = {}
    for log in logs:
        d = log["date"]
        if d not in log_map:
            log_map[d] = {}
        key = f"{log['medicine_id']}_{log['period']}"
        log_map[d][key] = log["cnt"]

    # 构建每日状态
    calendar = {}
    cur_day = first_day
    today = date.today()
    while cur_day <= last_day:
        d = cur_day.isoformat()
        if cur_day > today:
            calendar[d] = "future"
        elif d in log_map:
            # 检查是否有漏服
            taken_keys = set(log_map[d].keys())
            expected_keys = set(f"{m['id']}_{m['period']}" for m in all_meds)
            if expected_keys and expected_keys.issubset(taken_keys):
                calendar[d] = "full"
            elif taken_keys:
                calendar[d] = "partial"
            else:
                calendar[d] = "missed"
        else:
            calendar[d] = "missed" if cur_day < today else "future"
        cur_day += timedelta(days=1)

    return jsonify({"calendar": calendar, "year": year, "month": month})


@app.route("/api/med-day-detail", methods=["GET"])
def get_med_day_detail():
    """获取某天的服药详情"""
    date_str = request.args.get("date", date.today().isoformat())
    with get_db() as conn:
        logs = rows_to_list(conn.execute(
            """SELECT l.*, m.name as med_name, m.unit 
               FROM med_logs l JOIN medicines m ON l.medicine_id=m.id 
               WHERE l.date=? ORDER BY l.taken_at""",
            (date_str,)).fetchall())
        # 获取当天应服药计划
        schedules = rows_to_list(conn.execute(
            "SELECT m.id as medicine_id, m.name, ds.period, ds.label, ds.dose FROM medicines m JOIN dose_schedules ds ON m.id=ds.medicine_id WHERE ds.enabled=1"
        ).fetchall())
    return jsonify({"logs": logs, "schedules": schedules, "date": date_str})


# ═══════════════════════════════════════════════════════════════════════
# 血压心率 API
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/bp", methods=["GET"])
def get_bp():
    days = int(request.args.get("days", 30))
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        records = rows_to_list(conn.execute(
            "SELECT * FROM bp_records WHERE date>=? ORDER BY measured_at DESC",
            (since,)).fetchall())
    return jsonify(records)


@app.route("/api/bp", methods=["POST"])
def add_bp():
    data = request.get_json()
    measured_at = data.get("measured_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bp_records (measured_at, date, systolic, diastolic, pulse, note) VALUES (?,?,?,?,?,?)",
            (measured_at, measured_at[:10], data["systolic"], data["diastolic"],
             data.get("pulse"), data.get("note", ""))
        )
    return jsonify({"message": "记录成功"}), 201


@app.route("/api/bp/<int:rec_id>", methods=["DELETE"])
def delete_bp(rec_id):
    with get_db() as conn:
        conn.execute("DELETE FROM bp_records WHERE id=?", (rec_id,))
    return jsonify({"message": "删除成功"})


# ═══════════════════════════════════════════════════════════════════════
# 大便记录 API
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/bowel", methods=["GET"])
def get_bowel():
    limit = int(request.args.get("limit", 30))
    with get_db() as conn:
        records = rows_to_list(conn.execute(
            "SELECT * FROM bowel_records ORDER BY recorded_at DESC LIMIT ?", (limit,)).fetchall())
    return jsonify(records)


@app.route("/api/bowel", methods=["POST"])
def add_bowel():
    data = request.get_json() or {}
    recorded_at = data.get("recorded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    shape = data.get("shape")  # 布里斯托分型 1-7
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bowel_records (recorded_at, date, shape, note) VALUES (?,?,?,?)",
            (recorded_at, recorded_at[:10], shape, data.get("note", ""))
        )
    return jsonify({"message": "记录成功"}), 201


@app.route("/api/bowel/<int:rec_id>", methods=["PUT"])
def update_bowel(rec_id):
    data = request.get_json()
    recorded_at = data.get("recorded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    with get_db() as conn:
        conn.execute(
            "UPDATE bowel_records SET recorded_at=?, date=?, shape=?, note=? WHERE id=?",
            (recorded_at, recorded_at[:10], data.get("shape"), data.get("note", ""), rec_id)
        )
    return jsonify({"message": "更新成功"})


@app.route("/api/bowel/<int:rec_id>", methods=["DELETE"])
def delete_bowel(rec_id):
    with get_db() as conn:
        conn.execute("DELETE FROM bowel_records WHERE id=?", (rec_id,))
    return jsonify({"message": "删除成功"})


@app.route("/api/bowel/stats", methods=["GET"])
def bowel_stats():
    with get_db() as conn:
        records = rows_to_list(conn.execute(
            "SELECT * FROM bowel_records ORDER BY recorded_at DESC LIMIT 100").fetchall())

    if not records:
        return jsonify({"last": None, "hours_since": None, "avg_interval_hours": None, "count": 0})

    last_time = datetime.strptime(records[0]["recorded_at"], "%Y-%m-%d %H:%M:%S")
    hours_since = round((datetime.now() - last_time).total_seconds() / 3600, 1)

    # 计算平均间隔
    intervals = []
    for i in range(len(records) - 1):
        t1 = datetime.strptime(records[i]["recorded_at"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(records[i + 1]["recorded_at"], "%Y-%m-%d %H:%M:%S")
        intervals.append((t1 - t2).total_seconds() / 3600)

    avg = round(sum(intervals) / len(intervals), 1) if intervals else None

    return jsonify({
        "last": records[0]["recorded_at"],
        "hours_since": hours_since,
        "avg_interval_hours": avg,
        "count": len(records)
    })


# ═══════════════════════════════════════════════════════════════════════
# 数据备份与恢复
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/backup/json", methods=["GET"])
def backup_json():
    """完整 JSON 备份"""
    with get_db() as conn:
        data = {
            "backup_time": datetime.now().isoformat(),
            "version": "1.0",
            "medicines": rows_to_list(conn.execute("SELECT * FROM medicines").fetchall()),
            "dose_schedules": rows_to_list(conn.execute("SELECT * FROM dose_schedules").fetchall()),
            "med_logs": rows_to_list(conn.execute("SELECT * FROM med_logs").fetchall()),
            "bp_records": rows_to_list(conn.execute("SELECT * FROM bp_records").fetchall()),
            "bowel_records": rows_to_list(conn.execute("SELECT * FROM bowel_records").fetchall()),
        }

    buf = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    buf.seek(0)
    fname = f"health_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(buf, mimetype="application/json",
                     as_attachment=True, download_name=fname)


@app.route("/api/backup/csv", methods=["GET"])
def backup_csv():
    """CSV 导出（血压数据）"""
    table = request.args.get("table", "bp_records")
    allowed = {"bp_records", "med_logs", "bowel_records", "medicines"}
    if table not in allowed:
        return jsonify({"error": "不支持的表"}), 400

    with get_db() as conn:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            return jsonify({"error": "无数据"}), 404
        keys = rows[0].keys()

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys)
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))

    buf.seek(0)
    fname = f"{table}_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8-sig")),
                     mimetype="text/csv", as_attachment=True, download_name=fname)


@app.route("/api/restore", methods=["POST"])
def restore_json():
    """从 JSON 恢复数据"""
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    f = request.files["file"]
    try:
        data = json.loads(f.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": f"JSON 解析失败: {e}"}), 400

    with get_db() as conn:
        # 清空现有数据
        for table in ["med_logs", "dose_schedules", "medicines", "bp_records", "bowel_records"]:
            conn.execute(f"DELETE FROM {table}")

        # 恢复数据（跳过 id，让数据库自增）
        def restore_table(table_name, rows, skip_id=False):
            if not rows:
                return
            for row in rows:
                keys = [k for k in row.keys() if not (skip_id and k == "id")]
                vals = [row[k] for k in keys]
                placeholders = ",".join(["?"] * len(keys))
                col_str = ",".join(keys)
                conn.execute(f"INSERT OR REPLACE INTO {table_name} ({col_str}) VALUES ({placeholders})", vals)

        restore_table("medicines", data.get("medicines", []))
        restore_table("dose_schedules", data.get("dose_schedules", []))
        restore_table("med_logs", data.get("med_logs", []))
        restore_table("bp_records", data.get("bp_records", []))
        restore_table("bowel_records", data.get("bowel_records", []))

    return jsonify({"message": "数据恢复成功", "backup_time": data.get("backup_time", "未知")})


# ═══════════════════════════════════════════════════════════════════════
# 静态文件服务
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR / "templates"), "index.html")


@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ── 启动 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5555))
    print(f"[Server] 健康追踪应用启动: http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
