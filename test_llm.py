import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 无论从哪里运行，都读自己目录下的 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
if not api_key or api_key == "sk-xxxx":
    print("没读到有效的 DEEPSEEK_API_KEY，请检查 .env 是否填了真实 Key")
    sys.exit(1)

from openai import OpenAI

base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

client = OpenAI(api_key=api_key, base_url=base_url)

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是简洁的助手。"},
        {"role": "user", "content": "用一句话解释什么是 RAG（检索增强生成）。"},
    ],
    temperature=0.7,
)

print("调用成功")
print("模型回答：", resp.choices[0].message.content)
