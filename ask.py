"""M2 第 2 步：检索问答链（RAG）。

流程：用户问题 → bge 向量化 → Chroma 检索 TopK 相关 JD → 拼提示词 → 调 DeepSeek 回答。

关键设计：
- bge 模型 query 侧加前缀指令（bge 官方推荐用法），文档侧不加——提升检索质量
- 距离阈值：TopK 里 cosine 距离 > 0.5 的视为"不相关"，全部不相关就回答"检索不到"
- 提示词加防瞎编约束：只根据检索到的 JD 回答，检索不到就说不知道
"""
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL_PATH = str(Path(__file__).resolve().parent / "models" / "bge-small-zh-v1.5")
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION = "jobs"

TOP_K = 5
DISTANCE_THRESHOLD = 0.5  # cosine 距离阈值，> 0.5 判为不相关
# bge 官方推荐的 query 前缀（中文检索）
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def retrieve(query: str, top_k: int = TOP_K) -> list[tuple[str, dict, float]]:
    model = SentenceTransformer(MODEL_PATH)
    q_emb = model.encode([QUERY_PREFIX + query], normalize_embeddings=True).tolist()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(COLLECTION)
    if col.count() == 0:
        return []

    res = col.query(query_embeddings=q_emb, n_results=top_k)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist <= DISTANCE_THRESHOLD:
            hits.append((doc, meta, dist))
    return hits


def build_prompt(query: str, hits: list[tuple[str, dict, float]]) -> str:
    context = "\n\n".join(f"[{i + 1}] {doc}" for i, (doc, _, _) in enumerate(hits))
    return (
        "你是岗位情报助手。只根据下面检索到的岗位信息回答用户问题，"
        "不要编造检索结果里没有的内容；如果检索结果不足以回答，就明确说「检索不到相关信息」。\n\n"
        f"检索到的岗位信息：\n{context}\n\n"
        f"用户问题：{query}\n\n"
        "回答要求：\n"
        "1. 只引用上述岗位信息里的真实内容，涉及具体技术栈时点出岗位名称\n"
        "2. 检索不到就说不知道，不要瞎编"
    )


def ask(query: str) -> tuple[str, list[tuple[str, dict, float]]]:
    hits = retrieve(query)
    if not hits:
        return "检索不到相关信息。", hits

    prompt = build_prompt(query, hits)
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    resp = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content, hits


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "最近 Java岗都要求哪些技术？"
    answer, hits = ask(query)

    print(f"问题：{query}")
    print(f"检索到 {len(hits)} 条相关 JD：")
    for i, (_, meta, dist) in enumerate(hits, 1):
        print(f"  [{i}] {meta['title'][:40]} | 技术: {meta['tech_keywords'][:40]} | 距离: {dist:.3f}")
    print("=" * 60)
    print("回答：")
    print(answer)
