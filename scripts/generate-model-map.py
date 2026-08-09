#!/usr/bin/env python3
"""
从 models.dev/api.json 的 opencodezen 提供商节点生成模型映射
（上下文长度 + 思考强度档位）。

- 汉化时只需读取 opencodezen 节点（默认回退 opencode-go / opencode）
- api.json 缓存到 data/models-dev-api.json，网络失败时从缓存映射
- 生成 data/model-map.json: {"模型ID": {"ctx", "reasoning", "effort": [...]}}
  effort 为空数组表示无档位数据（应用按 reasoning 回退）

用法:
  python3 generate-model-map.py [--provider opencode-zen] [--source 路径或URL]
"""
import json
import os
import shutil
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
API_URL = "https://models.dev/api.json"
API_CACHE = os.path.join(DATA_DIR, "models-dev-api.json")
DEFAULT_PROVIDERS = ("opencode-zen", "opencode-go", "opencode")


def fetch_api(source):
    if source.startswith(("http://", "https://")):
        last_err = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = r.read()
                # 缓存到本地
                os.makedirs(DATA_DIR, exist_ok=True)
                tmp = API_CACHE + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                shutil.move(tmp, API_CACHE)
                print(f"已缓存到 {API_CACHE} ({len(data) // 1024} KB)")
                return json.loads(data)
            except Exception as e:
                last_err = e
                print(f"  第 {attempt + 1} 次尝试失败: {e}")
        raise last_err
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)


def get_effort(model_info):
    for opt in model_info.get("reasoning_options") or []:
        if isinstance(opt, dict) and opt.get("type") == "effort" and isinstance(opt.get("values"), list):
            return [v for v in opt["values"] if isinstance(v, str)]
    return []


def main():
    provider = "opencode-zen"
    source = None
    args = sys.argv[1:]
    if "--provider" in args:
        provider = args[args.index("--provider") + 1]
    if "--source" in args:
        source = args[args.index("--source") + 1]
    elif args and not args[0].startswith("--"):
        source = args[0]

    api = None
    if source:
        try:
            api = fetch_api(source)
        except Exception as e:
            print(f"错误: 无法获取 {source}: {e}")
            sys.exit(1)
    else:
        try:
            api = fetch_api(API_URL)
        except Exception as e:
            print(f"警告: 网络获取失败（{e}）")
            if os.path.exists(API_CACHE):
                print(f"使用本地缓存: {API_CACHE}")
                with open(API_CACHE, "r", encoding="utf-8") as f:
                    api = json.load(f)
            else:
                print("错误: 无本地缓存可用")
                sys.exit(1)

    # 选取 opencodezen 节点（回退链）
    chosen = None
    for pname in DEFAULT_PROVIDERS if provider == "opencode-zen" else (provider,):
        if isinstance(api.get(pname), dict) and isinstance(api[pname].get("models"), dict):
            chosen = pname
            break
    if not chosen:
        print(f"错误: 未找到提供商节点 {provider}（可用: {list(api.keys())[:10]}...）")
        sys.exit(1)

    models = api[chosen]["models"]
    out = {}
    for mid, info in models.items():
        if not isinstance(info, dict):
            continue
        ctx = None
        lim = info.get("limit")
        if isinstance(lim, dict) and isinstance(lim.get("context"), int):
            ctx = lim["context"]
        if ctx is None:
            continue
        entry = {"ctx": ctx, "reasoning": bool(info.get("reasoning"))}
        effort = get_effort(info)
        if effort:
            entry["effort"] = effort
        out[mid] = entry
        out[mid.lower()] = entry

    out_path = os.path.join(DATA_DIR, "model-map.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
    with_effort = sum(1 for e in out.values() if e.get("effort"))
    print(f"提供商节点: {chosen}（{len(models)} 模型）")
    print(f"已生成 {out_path}: {len(out)} 条（含 effort 档位: {with_effort}）")


if __name__ == "__main__":
    main()
