"""数据库层：SQLite 建表 + 连接管理。

M1 只用到 jobs 表；M2/M4 会复用这张表，字段名别乱改。
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,          -- 岗位名称
  company TEXT,                 -- 公司（种子数据里是类型标签，如"某AI SaaS创业公司"）
  city TEXT,                    -- 城市
  tech_keywords TEXT,           -- 技术关键词，逗号分隔
  degree TEXT,                  -- 学历要求
  url TEXT,                     -- 岗位链接
  crawled_at TEXT NOT NULL      -- 抓取时间，格式 YYYY-MM-DD
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


if __name__ == "__main__":
    init_db()
    print("jobs 表已就绪：", DB_PATH)
