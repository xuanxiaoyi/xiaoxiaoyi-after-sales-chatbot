import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None


DATA_DIR = Path(os.environ.get("APP_DATA_DIR", "data"))
EVIDENCE_DIR = DATA_DIR / "evidence"
SQLITE_PATH = DATA_DIR / "xiaoxiaoyi_app.db"

DEFAULT_USERS = [
    ("U1001", "张女士", "13800000001", "123456"),
    ("U1002", "李先生", "13800000002", "123456"),
]

DEFAULT_ORDERS = [
    (
        "EC20260702001",
        "U1001",
        "无线蓝牙耳机 Pro",
        "已签收",
        "签收时间为 2026-07-01 15:30。",
        "为保护订单信息，正式处理售后前还需要核验收货手机号后四位或收货人姓名。",
        "普通退货审核通常 24 小时内完成；质量问题审核通常 1 个工作日内完成。",
        "7 天内支持退货退款；15 天内质量问题支持换货；破损或功能异常需提供照片或视频。",
        "JD100120260702",
    ),
    (
        "EC20260702002",
        "U1001",
        "夏季纯棉 T 恤",
        "已发货",
        "物流单号 SF123456789CN，运输中，最近一次更新为 2026-07-02 09:20，已到达上海转运中心。",
        "如需拦截、改地址或登记物流核查，需要补充收货手机号后四位。",
        "物流超过 72 小时无更新可登记核查，核查通常 1 至 2 个工作日反馈。",
        "建议先等待签收；如物流超过 72 小时不更新，可登记物流核查。",
        "SF123456789CN",
    ),
    (
        "EC20260702003",
        "U1001",
        "便携榨汁杯",
        "已付款未发货",
        "订单尚未发货。",
        "取消订单前需要核验收货手机号后四位。",
        "取消申请通常 2 小时内审核；审核通过后 1 至 5 个工作日原路退款。",
        "可以直接申请取消订单，审核通过后原路退款。",
        "",
    ),
    (
        "EC20260702004",
        "U1002",
        "智能手表 S2",
        "退货退款处理中",
        "仓库已签收退货，正在验收。",
        "如需催促售后进度，请补充退货物流单号或收货手机号后四位。",
        "仓库验收通常 1 至 3 个工作日完成，验收通过后 1 至 5 个工作日原路退款。",
        "验收通常 1 至 3 个工作日完成，验收通过后 1 至 5 个工作日原路退款。",
        "YT20260702004",
    ),
    (
        "EC20260702005",
        "U1002",
        "护肤礼盒",
        "已签收",
        "护肤品属于特殊品类。",
        "如反馈破损、漏液或错发，需要补充照片、视频和快递面单照片。",
        "凭证齐全后通常 1 个工作日内完成初审。",
        "已拆封不支持无理由退货；如破损、漏液或错发，可提供照片申请售后。",
        "ZTO20260702005",
    ),
]


def now_text():
    return datetime.now().isoformat(timespec="microseconds")


def db_backend():
    return os.environ.get("APP_DB_BACKEND", "sqlite").lower()


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def mysql_config(include_database=True):
    config = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": True,
    }
    if include_database:
        config["database"] = os.environ.get("MYSQL_DATABASE", "xiaoxiaoyi_chatbot")
    return config


def ensure_mysql_database():
    if pymysql is None:
        raise RuntimeError("PyMySQL is not installed.")
    database = os.environ.get("MYSQL_DATABASE", "xiaoxiaoyi_chatbot")
    connection = pymysql.connect(**mysql_config(include_database=False))
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def connect():
    ensure_dirs()
    if db_backend() == "mysql":
        ensure_mysql_database()
        return pymysql.connect(
            **mysql_config(include_database=True),
            cursorclass=pymysql.cursors.DictCursor,
        )

    connection = sqlite3.connect(SQLITE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def placeholder():
    return "%s" if db_backend() == "mysql" else "?"


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def execute(connection, sql, params=()):
    cursor = connection.cursor()
    cursor.execute(sql, params)
    if db_backend() != "mysql":
        connection.commit()
    return cursor


def init_app_database():
    ensure_dirs()
    mark = placeholder()
    connection = connect()
    try:
        execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(32) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL,
                created_at VARCHAR(32) NOT NULL
            )
            """,
        )
        execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                product TEXT NOT NULL,
                status VARCHAR(100) NOT NULL,
                detail TEXT NOT NULL,
                verify TEXT NOT NULL,
                sla TEXT NOT NULL,
                solution TEXT NOT NULL,
                logistics_no VARCHAR(100),
                updated_at VARCHAR(32) NOT NULL
            )
            """,
        )
        execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64),
                order_id VARCHAR(64),
                category VARCHAR(80) NOT NULL,
                status VARCHAR(80) NOT NULL,
                priority VARCHAR(40) NOT NULL,
                description TEXT NOT NULL,
                latest_progress TEXT NOT NULL,
                created_at VARCHAR(32) NOT NULL,
                updated_at VARCHAR(32) NOT NULL
            )
            """,
        )
        execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS conversations (
                message_id VARCHAR(64) PRIMARY KEY,
                session_id VARCHAR(128) NOT NULL,
                user_id VARCHAR(64),
                channel VARCHAR(40) NOT NULL,
                role VARCHAR(40) NOT NULL,
                content TEXT NOT NULL,
                created_at VARCHAR(32) NOT NULL
            )
            """,
        )
        execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS evidence_files (
                file_id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64),
                order_id VARCHAR(64),
                ticket_id VARCHAR(64),
                original_name TEXT NOT NULL,
                saved_path TEXT NOT NULL,
                purpose VARCHAR(100) NOT NULL,
                created_at VARCHAR(32) NOT NULL
            )
            """,
        )

        for user in DEFAULT_USERS:
            if db_backend() == "mysql":
                sql = (
                    "INSERT IGNORE INTO users "
                    "(user_id, name, phone, password, created_at) VALUES "
                    f"({mark}, {mark}, {mark}, {mark}, {mark})"
                )
            else:
                sql = (
                    "INSERT OR IGNORE INTO users "
                    "(user_id, name, phone, password, created_at) VALUES "
                    f"({mark}, {mark}, {mark}, {mark}, {mark})"
                )
            execute(connection, sql, (*user, now_text()))

        for order in DEFAULT_ORDERS:
            if db_backend() == "mysql":
                sql = (
                    "INSERT IGNORE INTO orders "
                    "(order_id, user_id, product, status, detail, verify, sla, solution, logistics_no, updated_at) "
                    f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark})"
                )
            else:
                sql = (
                    "INSERT OR IGNORE INTO orders "
                    "(order_id, user_id, product, status, detail, verify, sla, solution, logistics_no, updated_at) "
                    f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark})"
                )
            execute(connection, sql, (*order, now_text()))
    finally:
        connection.close()


def get_user_by_phone(phone, password=None):
    init_app_database()
    mark = placeholder()
    connection = connect()
    try:
        cursor = connection.cursor()
        if password is None:
            cursor.execute(f"SELECT * FROM users WHERE phone = {mark}", (phone,))
        else:
            cursor.execute(
                f"SELECT * FROM users WHERE phone = {mark} AND password = {mark}",
                (phone, password),
            )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_order(order_id, user_id=None):
    init_app_database()
    mark = placeholder()
    connection = connect()
    try:
        cursor = connection.cursor()
        if user_id:
            cursor.execute(
                f"SELECT * FROM orders WHERE order_id = {mark} AND user_id = {mark}",
                (order_id, user_id),
            )
        else:
            cursor.execute(f"SELECT * FROM orders WHERE order_id = {mark}", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def list_orders(user_id=None):
    init_app_database()
    mark = placeholder()
    connection = connect()
    try:
        cursor = connection.cursor()
        if user_id:
            cursor.execute(
                f"SELECT order_id, product, status, detail, logistics_no, updated_at FROM orders "
                f"WHERE user_id = {mark} ORDER BY updated_at DESC, order_id DESC",
                (user_id,),
            )
        else:
            cursor.execute(
                "SELECT order_id, user_id, product, status, detail, logistics_no, updated_at "
                "FROM orders ORDER BY updated_at DESC, order_id DESC"
            )
        return rows_to_dicts(cursor.fetchall())
    finally:
        connection.close()


def save_message(session_id, role, content, user_id=None, channel="web"):
    init_app_database()
    mark = placeholder()
    connection = connect()
    try:
        execute(
            connection,
            "INSERT INTO conversations "
            "(message_id, session_id, user_id, channel, role, content, created_at) "
            f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark})",
            (str(uuid.uuid4()), session_id, user_id, channel, role, content, now_text()),
        )
    finally:
        connection.close()


def get_recent_messages(session_id, limit=12):
    init_app_database()
    mark = placeholder()
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT role, content FROM conversations "
            f"WHERE session_id = {mark} ORDER BY created_at DESC LIMIT {int(limit)}",
            (session_id,),
        )
        rows = rows_to_dicts(cursor.fetchall())
        rows.reverse()
        return rows
    finally:
        connection.close()


def list_conversations(limit=80):
    init_app_database()
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT created_at, channel, user_id, session_id, role, content "
            f"FROM conversations ORDER BY created_at DESC LIMIT {int(limit)}"
        )
        return rows_to_dicts(cursor.fetchall())
    finally:
        connection.close()


def detect_ticket_category(text):
    if any(word in text for word in ["投诉", "不满意", "太慢", "没人处理", "升级"]):
        return "投诉升级"
    if any(word in text for word in ["人工", "真人", "转人工"]):
        return "人工客服"
    if any(word in text for word in ["物流核查", "没更新", "丢件", "快递"]):
        return "物流核查"
    if any(word in text for word in ["退款", "退货", "退钱"]):
        return "退款进度"
    if any(word in text for word in ["破损", "错发", "少件", "漏发", "质量"]):
        return "凭证审核"
    return "售后咨询"


def should_create_ticket(text):
    return any(
        word in text
        for word in [
            "投诉", "不满意", "太慢", "没人处理", "人工", "转人工", "物流核查",
            "丢件", "退款进度", "破损", "错发", "少件", "漏发",
        ]
    )


def create_ticket(description, user_id=None, order_id=None, category=None, priority="普通"):
    init_app_database()
    mark = placeholder()
    category = category or detect_ticket_category(description)
    ticket_id = "TK" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()
    progress = "已登记，等待客服复核。"
    connection = connect()
    try:
        execute(
            connection,
            "INSERT INTO tickets "
            "(ticket_id, user_id, order_id, category, status, priority, description, latest_progress, created_at, updated_at) "
            f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark})",
            (
                ticket_id,
                user_id,
                order_id,
                category,
                "待处理",
                priority,
                description,
                progress,
                now_text(),
                now_text(),
            ),
        )
        return ticket_id
    finally:
        connection.close()


def list_tickets(limit=80):
    init_app_database()
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT ticket_id, user_id, order_id, category, status, priority, latest_progress, created_at, updated_at "
            f"FROM tickets ORDER BY updated_at DESC LIMIT {int(limit)}"
        )
        return rows_to_dicts(cursor.fetchall())
    finally:
        connection.close()


def list_evidence_files(limit=80):
    init_app_database()
    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT created_at, user_id, order_id, ticket_id, original_name, saved_path, purpose "
            f"FROM evidence_files ORDER BY created_at DESC LIMIT {int(limit)}"
        )
        return rows_to_dicts(cursor.fetchall())
    finally:
        connection.close()


def save_evidence_file(file_path, user_id=None, order_id=None, ticket_id=None, purpose="售后凭证"):
    init_app_database()
    if not file_path:
        return None

    source = Path(file_path)
    if not source.exists():
        return None

    file_id = str(uuid.uuid4())
    suffix = source.suffix or ".bin"
    target = EVIDENCE_DIR / f"{file_id}{suffix}"
    shutil.copy2(source, target)

    mark = placeholder()
    connection = connect()
    try:
        execute(
            connection,
            "INSERT INTO evidence_files "
            "(file_id, user_id, order_id, ticket_id, original_name, saved_path, purpose, created_at) "
            f"VALUES ({mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark}, {mark})",
            (
                file_id,
                user_id,
                order_id,
                ticket_id,
                source.name,
                str(target),
                purpose,
                now_text(),
            ),
        )
        return str(target)
    finally:
        connection.close()
