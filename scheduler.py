"""定时抓取：每天固定时间跑 crawler，按 url 去重增量入库。

用法：
- 立即执行一次（验收去重用）：python scheduler.py --run-once
- 启动常驻定时任务：python scheduler.py  （每天 09:00 抓取，Ctrl+C 退出）

助记：爬虫是手，定时器是闹钟，SQLite 是仓库。
"""
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from crawler import crawl


def daily_crawl():
    r = crawl()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[{now}] 每日抓取完成：列表 {r['total_rows']} 条，"
        f"新增 {r['inserted']} 条，跳过(已存在) {r['skipped']} 条"
    )


scheduler = BlockingScheduler(timezone="Asia/Shanghai")
scheduler.add_job(daily_crawl, CronTrigger(hour=9, minute=0), id="daily_crawl")


if __name__ == "__main__":
    if "--run-once" in sys.argv:
        daily_crawl()  # 立即跑一次，第二次跑应全是"跳过"（验证去重）
    else:
        print("定时任务已启动：每天 09:00 抓取（按 Ctrl+C 退出）")
        scheduler.start()
