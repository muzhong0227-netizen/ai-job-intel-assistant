# AI 岗位情报助手

一个「定时抓取岗位 → 向量化入库 → RAG 问答 → Function Calling 统计」的完整 Demo。
技术栈：Python + SQLite + ChromaDB + sentence-transformers(bge) + LangChain + DeepSeek。

> 用途：毕设前置练手。毕设后端调 DeepSeek 就是这套路，只是提示词换成简历诊断的。

---

## 里程碑进度

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 环境 + 调通 DeepSeek API | ✅ |
| M1 | 建表 + 种子入库 + 爬虫 + 定时 | ✅ |
| M2 | 向量化入库 + RAG 检索问答（核心亮点） | ✅ |
| M3 | Function Calling 统计 | ✅ |
| M4 | 飞书 Webhook 推送（可砍） | ⏸ 未做 |

---

## 文件清单

| 文件 | 作用 | 里程碑 |
|---|---|---|
| `test_llm.py` | 调 DeepSeek 解释 RAG（M0 验收） | M0 |
| `db.py` | SQLite 建 `jobs` 表 + 连接管理 | M1 |
| `seed_import.py` | 导入 `seed_jds.json` 20 条种子数据 | M1 |
| `seed_jds.json` | 20 条种子岗位 | M1 |
| `crawler.py` | 抓思否「酷工作」招聘帖 | M1 |
| `scheduler.py` | APScheduler 每天 09:00 定时抓取 | M1 |
| `download_model.py` | 下载 bge 模型到本地 `models/` | M2 |
| `rag_index.py` | JD 向量化入库 Chroma | M2 |
| `ask.py` | RAG 检索问答链 | M2 |
| `tools.py` | `query_jobs` / `count_by_tech` 本地函数 | M3 |
| `stats.py` | Function Calling 统计链 | M3 |

数据文件：`jobs.db`（40 条岗位）、`chroma_db/`（向量库）、`models/bge-small-zh-v1.5/`（本地模型）。

---

## 运行方式

所有命令在 `ai-job-intel/` 目录下、用项目 venv 执行：

```bash
# 前置：venv 里装依赖（见 M0；本机 pip 需加 --index-url https://pypi.org/simple）

# M0 验收：调 DeepSeek
.venv/Scripts/python.exe test_llm.py

# M1：建表 + 导入种子 + 爬虫 + 定时
.venv/Scripts/python.exe db.py
.venv/Scripts/python.exe seed_import.py
.venv/Scripts/python.exe crawler.py
.venv/Scripts/python.exe scheduler.py --run-once   # 手动触发一次

# M2：向量化 + 问答（先下载模型，见下）
.venv/Scripts/python.exe download_model.py
.venv/Scripts/python.exe rag_index.py
.venv/Scripts/python.exe ask.py "最近 Java 实习岗都要求哪些技术？"

# M3：Function Calling 统计
.venv/Scripts/python.exe stats.py "Python 岗有多少个？最火的技术是哪个？"
```

配置：`.env` 里填 `DEEPSEEK_API_KEY`（`.env` 已被 `.gitignore` 排除，不提交）。

---

## 验收结果（M0–M3）

- **M0**：`test_llm.py` 调 `deepseek-chat` 成功，模型用一句话解释 RAG。
- **M1**：`jobs` 表 40 条（20 种子 + 20 思否真实抓取）；爬虫按 url 去重，二次触发 0 重复。
- **M2**：Chroma 向量数 = 40 = JD 条数；问「Java 实习岗」正确命中 Java 岗并引用真实技术词；问「量子计算机」诚实答「检索不到」——防瞎编约束生效。
- **M3**：模型自动调 `query_jobs` + `count_by_tech` 两个函数，统计数字（Python 21 / RAG 12 / LangChain 10）与数据库完全一致。

---

## 关键踩坑记录（Windows 环境）

这些坑以后自己开发还会遇到，已全部解决：

| 坑 | 现象 | 解决 |
|---|---|---|
| pip 清华源 | `from versions: none` | 加 `--index-url https://pypi.org/simple` |
| openai 客户端 | 首次跑 SIGTERM 无输出 | `python -u` 关缓冲 |
| PyCharm 解释器 | `No module named dotenv` | 切到 `ai-job-intel\.venv` |
| 爬虫 UA 中文 | `UnicodeEncodeError` | HTTP header 只支持 latin-1，改英文 |
| huggingface_hub xet | 下载模型 401 | `HF_HUB_DISABLE_XET=1` |
| Windows 模型下载 | symlink 留 0 字节 + 临时文件清理被沙箱拦截 | requests 直下到本地目录 |
| Chroma 距离函数 | 默认 L2（量纲 0-4），0.5 阈值挡掉正确结果 | collection 指定 `metadata={"hnsw:space":"cosine"}` |
| query_jobs LIMIT | Python 岗 21 条被截断成 20 | 去掉 LIMIT |

**数据源选型**（实测结论）：V2EX 酷工作国内被墙、电鸭有 CAPTCHA、开源中国招聘已下线 → 选**思否酷工作**（国内可达、SSR 无登录墙）。

---

## 面试话术汇总

- **M1 入库**：「先拿种子数据把入库链路跑通，再替换真实抓取——这是防翻车的做法。」
- **M2 RAG**：「RAG 解决大模型瞎编岗位信息的问题——先翻资料，再开口回答。」
- **M3 Function Calling**：「Function Calling 让模型从『只会聊天』变成『会动手查数据』，这是 Agent 思想的雏形。」

---

## 数据现状

- `jobs.db`：40 条岗位 = 20 种子（类型标签公司）+ 20 思否真实抓取。
- 真实抓取字段质量：city 17/20、tech_keywords 17/20、company 6/20（社区帖自由文本，公司字段天然难提，不影响 M2/M3）。
