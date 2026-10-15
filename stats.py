"""M3 第 2 步：Function Calling 统计。

流程：用户问题 → 调 DeepSeek（带 tools）→ 模型返回 tool_calls → 执行本地函数
     → 结果喂回模型 → 模型总结成自然语言。

用法：python stats.py "Python 岗有多少个？最火的技术是哪个？"

助记：问答靠嘴，统计靠手——Function Calling 就是给模型长手。
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools import count_by_tech, query_jobs

load_dotenv(Path(__file__).resolve().parent / ".env")

FUNC_MAP = {
    "query_jobs": query_jobs,
    "count_by_tech": count_by_tech,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_jobs",
            "description": "按技术关键词和城市查询岗位列表，返回岗位的标题、公司、城市、技术关键词、学历",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "技术关键词，如 Python、Java"},
                    "city": {"type": "string", "description": "城市，如 北京、上海，留空表示不限城市"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_by_tech",
            "description": "统计数据库里各技术关键词出现的岗位次数，返回出现次数最多的前 N 名",
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "description": "返回前 N 名，默认 10"},
                },
            },
        },
    },
]


def run(question: str) -> str:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    messages = [{"role": "user", "content": question}]

    # 第一轮：模型决定是否调函数
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = resp.choices[0].message

    if not msg.tool_calls:
        # 模型没调函数，直接回答（可能它认为不需要查数据）
        return msg.content

    # 执行本地函数
    messages.append(msg)  # 把 assistant 的 tool_calls 消息加回对话
    for tc in msg.tool_calls:
        fn_name = tc.function.name
        fn_args = json.loads(tc.function.arguments or "{}")
        print(f"[模型调用] {fn_name}({fn_args})")
        result = FUNC_MAP[fn_name](**fn_args)
        print(f"[函数结果] 返回 {len(result) if isinstance(result, list) else '统计'} 项")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    # 第二轮：模型基于函数结果总结
    resp2 = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return resp2.choices[0].message.content


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Python 岗有多少个？最火的技术是哪个？"
    print(f"问题：{question}")
    print("=" * 60)
    answer = run(question)
    print("=" * 60)
    print("回答：")
    print(answer)
