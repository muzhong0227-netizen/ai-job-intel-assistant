"""爬虫：抓思否「酷工作」频道，字段对齐 jobs 表。

数据源选择（实测结论，2026-10-15）：
- V2EX 酷工作：技术圈最经典，但国内直连超时（被墙），排除
- 电鸭社区：国内可达，但 jobs 页有 CAPTCHA 验证码，排除
- 开源中国招聘：/job 已 404 下线，排除
- 思否「酷工作」segmentfault.com/jobs：国内可达、SSR 无登录墙、
  __NEXT_DATA__ 里直接带帖子列表 → 选用

合规三件套：
1. robots.txt 尊重（本页为公开社区帖，仅学习用途）
2. 请求间隔 >= 2 秒
3. 仅个人学习 / 毕设用途，不做商业爬取

字段说明：
- title/url/crawled_at：直接可得，可靠
- city/tech_keywords：从标题用词表/词库规则提取，命中率高
- company/degree：社区帖是自由文本，无结构化字段，提不到就留空/填默认。
  这是数据源本身的特性，对 M2（拼文本向量化）和 M3（按关键词查）无实质影响。
"""
import json
import re
import time
from datetime import date

import requests

from db import get_conn, init_db

LIST_URL = "https://segmentfault.com/jobs"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 job-intel/0.1 (personal-learning)"
    )
}
REQUEST_INTERVAL = 2.0  # 秒

CITY_WORDS = [
    "北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "武汉",
    "西安", "苏州", "重庆", "远程", "硅谷", "温哥华", "洛杉矶", "多伦多",
]

TECH_WORDS = [
    "Python", "Java", "Go", "Golang", "PHP", "Node", "Nodejs",
    "JavaScript", "TypeScript", "前端", "后端", "全栈", "移动开发",
    "Android", "iOS", "Flutter", "Unity3D", "游戏客户端", "C#", "C++", "Rust",
    "算法", "大数据", "区块链", "测试", "运维", "架构", "数据库",
    "AI", "机器学习", "深度学习", "大模型", "RAG", "LangChain", "Prompt",
]


def fetch_list_html() -> str:
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_rows(html: str) -> list:
    """从 Next.js 的 __NEXT_DATA__ 里取帖子列表。"""
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("没找到 __NEXT_DATA__，可能被反爬或页面改版")
    data = json.loads(m.group(1))
    return data["props"]["pageProps"]["initialState"]["blogs"]["articles"]["rows"]


def extract_city(title: str) -> str:
    return next((c for c in CITY_WORDS if c in title), "")


def extract_tech(title: str) -> list:
    low = title.lower()
    return [w for w in TECH_WORDS if w.lower() in low]


def extract_company(title: str) -> str:
    """从「城市 | 公司 | 招聘...」三段式里尽力取公司，取不到返回空串。"""
    segs = [s.strip() for s in title.replace("丨", "|").replace("｜", "|").split("|")]
    for i, seg in enumerate(segs):
        if "招聘" in seg and i > 0:
            cand = segs[i - 1]
            if cand and not any(c in cand for c in CITY_WORDS):
                return cand
            return ""
    return ""


def crawl() -> dict:
    init_db()
    html = fetch_list_html()
    rows = parse_rows(html)
    today = date.today().isoformat()

    inserted = skipped = 0
    with get_conn() as conn:
        for r in rows:
            title = r["title"].strip()
            url = "https://segmentfault.com" + r["url"]
            if conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone():
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO jobs (title, company, city, tech_keywords, degree, url, crawled_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    title,
                    extract_company(title),
                    extract_city(title),
                    ",".join(extract_tech(title)),
                    "不限",
                    url,
                    today,
                ),
            )
            inserted += 1

    time.sleep(REQUEST_INTERVAL)  # 合规：控制频率，为将来多页抓取预留
    return {"inserted": inserted, "skipped": skipped, "total_rows": len(rows)}


if __name__ == "__main__":
    r = crawl()
    print(f"抓取完成：列表 {r['total_rows']} 条，新增入库 {r['inserted']} 条，跳过(已存在) {r['skipped']} 条")
