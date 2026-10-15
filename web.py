# web.py —— 给 RAG 问答套个 Web 壳（复用 M2 已跑通的 ask.py 逻辑）
#
# 依赖：pip install fastapi uvicorn（其余 M2 已装）
# 运行：在 ai-job-intel/ 目录下执行 uvicorn web:app --reload
#      或直接 python web.py（内置 uvicorn 启动）
# 打开：http://127.0.0.1:8000

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent / ".env")

import chromadb  # noqa: E402
from openai import OpenAI  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from ask import build_prompt  # 复用 M2 已验收的提示词逻辑

# ============ 配置：跟 M2（ask.py）保持一致 ============
MODEL_PATH = str(Path(__file__).resolve().parent / "models" / "bge-small-zh-v1.5")
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION = "jobs"
TOP_K = 4
DISTANCE_THRESHOLD = 0.5
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
# =====================================================

print("正在加载向量模型和向量库，稍等十几秒...")
embed_model = SentenceTransformer(MODEL_PATH)
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_or_create_collection(COLLECTION)
llm = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)
LLM_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
print("加载完成，服务就绪。")


def retrieve(query: str, top_k: int = TOP_K) -> list[tuple[str, dict, float]]:
    q_emb = embed_model.encode([QUERY_PREFIX + query], normalize_embeddings=True).tolist()
    if collection.count() == 0:
        return []
    res = collection.query(query_embeddings=q_emb, n_results=top_k)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if dist <= DISTANCE_THRESHOLD:
            hits.append((doc, meta, dist))
    return hits


def rag_answer(question: str) -> tuple[str, list[dict]]:
    hits = retrieve(question)
    if not hits:
        return "检索不到相关岗位信息。", []

    prompt = build_prompt(question, hits)
    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    answer = resp.choices[0].message.content
    sources = [
        {
            "title": meta.get("title", ""),
            "company": meta.get("company", ""),
            "tech_keywords": meta.get("tech_keywords", ""),
        }
        for _, meta, _ in hits
    ]
    return answer, sources


app = FastAPI(title="AI 岗位情报助手")


class AskReq(BaseModel):
    question: str


@app.post("/ask")
def ask(req: AskReq):
    answer, sources = rag_answer(req.question.strip())
    return {"answer": answer, "sources": sources}


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).resolve().parent / "index.html"
    return html_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
