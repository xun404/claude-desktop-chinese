#!/usr/bin/env python3
"""
从 models.dev 生成模型映射数据（上下文长度 + 思考强度）。

用法:
  python3 generate-model-map.py [--source models.dev/models.json 路径或 URL]

生成 data/model-map.json:
  {"模型ID": {"ctx": 上下文长度, "reasoning": 是否推理模型}}
"""
import json
import os
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
SOURCE = "https://models.dev/models.json"


def fetch_source(source):
    if source.startswith(("http://", "https://")):
        print(f"下载 {source} ...")
        last_err = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)
            except Exception as e:
                last_err = e
                print(f"  第 {attempt + 1} 次尝试失败: {e}")
        raise last_err
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    source = SOURCE
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        source = sys.argv[1]

    try:
        raw = fetch_source(source)
    except Exception as e:
        print(f"错误: 无法获取 {source}: {e}")
        sys.exit(1)

    if not isinstance(raw, dict):
        print("错误: 期望 JSON 对象（provider/model-id -> 模型信息）")
        sys.exit(1)

    out = {}
    for mid, info in raw.items():
        if not isinstance(info, dict):
            continue
        ctx = info.get("limit", {}).get("context") if isinstance(info.get("limit"), dict) else None
        if not isinstance(ctx, int):
            continue
        # 使用斜杠后的裸模型 ID 作为键，保留原始大小写，同时提供小写别名
        bare = mid.split("/")[-1]
        entry = {"ctx": ctx, "reasoning": bool(info.get("reasoning"))}
        out[bare] = entry
        out[bare.lower()] = entry

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "model-map.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"已生成 {out_path}: {len(out)} 条（{len(raw)} 个源模型）")


if __name__ == "__main__":
    main()
