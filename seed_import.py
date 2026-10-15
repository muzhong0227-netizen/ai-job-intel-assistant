"""种子数据导入：把 seed_jds.json 的 20 条岗位导进 jobs 表。

先拿种子数据把入库链路跑通，再替换真实抓取——防翻车。
按 url 去重，重复跑不会累积重复数据。
"""
import json
from pathlib import Path

from db import get_conn, init_db

SEED_PATH = Path(__file__).resolve().parent / "seed_jds.json"


def import_seed() -> dict:
    init_db()
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    inserted = 0
    skipped = 0
    with get_conn() as conn:
        for d in data:
            exists = conn.execute(
                "SELECT 1 FROM jobs WHERE url = ?", (d["url"],)
            ).fetchone()
            if exists:
                skipped += 1
                continue
            conn.execute(
                """
                INSERT INTO jobs (title, company, city, tech_keywords, degree, url, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["title"],
                    d["company"],
                    d["city"],
                    ",".join(d["tech_keywords"]),  # 数组 -> 逗号分隔字符串
                    d["degree"],
                    d["url"],
                    d["crawled_at"],
                ),
            )
            inserted += 1

    total = get_conn().execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    return {"inserted": inserted, "skipped": skipped, "total": total}


if __name__ == "__main__":
    r = import_seed()
    print(f"导入完成：新增 {r['inserted']} 条，跳过 {r['skipped']} 条，库内共 {r['total']} 条")
