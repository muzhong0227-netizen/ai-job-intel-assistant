"""下载 bge 模型到项目本地 models/ 目录（用 requests 直下，绕过 huggingface_hub）。

为什么不用 huggingface_hub：
1. 新版默认走 xet 协议，hf-mirror 没代理 xet 的 CAS 服务器 → 401
2. 下载时的 .lock/.incomplete 临时文件清理会被环境沙箱 safe-delete 拦截

改用 requests 直接写目标文件（只写不删），两个坑都绕开。
"""
from pathlib import Path

import requests

BASE = "https://hf-mirror.com/BAAI/bge-small-zh-v1.5/resolve/main/"
TARGET = Path(__file__).resolve().parent / "models" / "bge-small-zh-v1.5"

# 只需要这些：safetensors 替代 pytorch_model.bin（sentence-transformers 优先用 safetensors）
FILES = [
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "1_Pooling/config.json",
]


def download() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        dest = TARGET / f
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = BASE + f
        print(f"下载 {f} ...", flush=True)
        r = requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0) or 0)
        done = 0
        with open(dest, "wb") as fp:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                fp.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {f}: {done / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB", end="", flush=True)
        print()
    print("全部下载完成:", TARGET)


if __name__ == "__main__":
    download()
