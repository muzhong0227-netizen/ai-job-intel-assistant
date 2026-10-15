"""M3 第 1 步：本地查询函数（直连 SQLite）。

Function Calling 的"手"——模型不直接碰数据库，通过调用这些函数查数据。
先保证函数本身是对的（数字跟数据库 COUNT 对得上），再让模型调它。
"""
from collections import Counter

from db import get_conn


def query_jobs(keyword: str = "", city: str = "") -> list[dict]:
    """按技术关键词和城市查岗位列表。

    Args:
        keyword: 技术关键词（模糊匹配 tech_keywords 或 title），如 "Python"
        city: 城市（精确匹配），如 "北京"，留空则不限制
    """
    sql = "SELECT id, title, company, city, tech_keywords, degree FROM jobs WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (tech_keywords LIKE ? OR title LIKE ?)"
        kw = f"%{keyword}%"
        params += [kw, kw]
    if city:
        sql += " AND city = ?"
        params.append(city)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def count_by_tech(top_n: int = 10) -> list[dict]:
    """统计各技术关键词出现次数，返回 Top N。

    tech_keywords 是逗号分隔字符串，先拆分再计数。
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT tech_keywords FROM jobs WHERE tech_keywords IS NOT NULL AND tech_keywords != ''"
        ).fetchall()

    counter: Counter = Counter()
    for r in rows:
        for kw in r["tech_keywords"].split(","):
            kw = kw.strip()
            if kw:
                counter[kw] += 1

    return [{"keyword": k, "count": v} for k, v in counter.most_common(top_n)]


if __name__ == "__main__":
    print("=== count_by_tech Top10 ===")
    for item in count_by_tech(10):
        print(f"  {item['keyword']}: {item['count']}")

    print("\n=== query_jobs('Python') 前 5 条 ===")
    for j in query_jobs(keyword="Python")[:5]:
        print(f"  [{j['city']}] {j['title'][:30]} | {j['tech_keywords'][:40]}")

    print("\n=== query_jobs('', '北京') 前 5 条 ===")
    for j in query_jobs(city="北京")[:5]:
        print(f"  [{j['city']}] {j['title'][:30]} | {j['tech_keywords'][:40]}")
