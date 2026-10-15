"""M2 第 1 步：向量化入库。

流程：SQLite 读 JD → 拼文本（标题+公司+城市+技术关键词）→ bge-small-zh-v1.5 向量化 → 存 Chroma。

bge 模型从 HuggingFace 下载，国内用镜像（跑之前先 export）：
    export HF_ENDPOINT=https://hf-mirror.com

验收：Chroma 向量数 == JD 条数。
"""
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from db import get_conn

# 模型已下载到本地 models/ 目录（见 download_model.py），用本地路径加载，不依赖网络
MODEL_NAME = str(Path(__file__).resolve().parent / "models" / "bge-small-zh-v1.5")
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION = "jobs"


def load_jobs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, company, city, tech_keywords, degree, url FROM jobs"
        ).fetchall()
    return [dict(r) for r in rows]


def build_doc(job: dict) -> str:
    parts = [job["title"]]
    if job["company"]:
        parts.append(f"公司：{job['company']}")
    if job["city"]:
        parts.append(f"城市：{job['city']}")
    if job["tech_keywords"]:
        parts.append(f"技术要求：{job['tech_keywords']}")
    if job["degree"]:
        parts.append(f"学历：{job['degree']}")
    return "。".join(parts)


def main() -> None:
    jobs = load_jobs()
    print(f"从 SQLite 读到 {len(jobs)} 条 JD")

    docs = [build_doc(j) for j in jobs]

    print(f"加载模型 {MODEL_NAME} ...（首次下载，慢是正常的）")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(docs, normalize_embeddings=True).tolist()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # 重建 collection，保证幂等：向量数始终 == JD 条数
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    col.add(
        ids=[f"job-{j['id']}" for j in jobs],
        embeddings=embeddings,
        documents=docs,
        metadatas=[
            {
                "title": j["title"] or "",
                "company": j["company"] or "",
                "city": j["city"] or "",
                "tech_keywords": j["tech_keywords"] or "",
                "url": j["url"] or "",
            }
            for j in jobs
        ],
    )

    print(f"向量化入库完成：Chroma 向量数 = {col.count()}")


if __name__ == "__main__":
    main()
