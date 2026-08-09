#!/usr/bin/env python3
"""
将 data/model-map.json 嵌入 app.asar（模型上下文长度 + 思考强度映射）。

用法:
  python3 patch-model-map.py [Resources路径]

默认 Resources 路径: /Applications/Claude.app/Contents/Resources

补丁内容（index.chunk-w2M3Ll-M.js）:
  1. 注入 var MdlMap=JSON.parse("...")  （models.dev 紧凑映射）
  2. sd(): supports1m 由映射 ctx>=1e6 决定 → 自动生成 [1m] 变体
  3. Hu(): 思考强度由映射 reasoning 决定 → 无目录元数据时回退 ju

需要 npx（@electron/asar）。替换后需重新签名（见 llms.txt 签名流程）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
MODEL_MAP = os.path.join(DATA_DIR, "model-map.json")
CHUNK_REL = os.path.join(".vite", "build", "index.chunk-w2M3Ll-M.js")
UNPACK_GLOB = "{**/node_modules/@ant/**,**/node_modules/node-pty/**,**/resources/github-mcp/**,**/resources/office365-mcp/**}"


def find_resources_dir():
    if len(sys.argv) > 1:
        return sys.argv[1]
    default = "/Applications/Claude.app/Contents/Resources"
    if os.path.isdir(default):
        return default
    print("错误: 未找到 Resources 目录，请手动指定路径")
    sys.exit(1)


def run_npx(args):
    subprocess.run(["npx", "--yes", "@electron/asar", *args], check=True)


def build_map_literal():
    with open(MODEL_MAP, "r", encoding="utf-8") as f:
        d = json.load(f)
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    esc = js.replace("\\", "\\\\").replace('"', '\\"')
    return 'var MdlMap=JSON.parse("' + esc + '");'


def patch_chunk(chunk_path):
    c = open(chunk_path, "r", encoding="utf-8").read()
    changed = []

    # 1. 注入/更新 MdlMap
    m = re.search(r'var MdlMap=JSON\.parse\("[^"]*"\);', c)
    literal = build_map_literal()
    if m:
        c = c.replace(m.group(0), literal, 1)
        changed.append("更新 MdlMap 映射")
    else:
        marker = "function sd(e){"
        if marker not in c:
            print(f"  跳过: 未找到 sd() 锚点 ({chunk_path})")
            return False
        c = c.replace(marker, literal + marker, 1)
        changed.append("注入 MdlMap 映射")

    # 2. sd(): supports1m 由映射 ctx 决定
    if "MdlMap[e.id.toLowerCase()]||{}).ctx??0)>=1e6" not in c:
        old_sd = 'function sd(e){let t=e.models.flatMap(e=>{let t={id:e.id,name:e.labelOverride??e.name,description:ad(e.id),thinking:Hu(e.id),...e.restricted&&wu(e.labelOverride??e.name)};return!e.supports1m||e.restricted?[t]:[t,{...t,id:`${e.id}[1m]`,description:od,supports_1m_context:!0}]});return Wu.map(e=>({id:e,models:t}))}'
        new_sd = 'function sd(e){let t=e.models.flatMap(e=>{let s=!!e.supports1m||((MdlMap[e.id.toLowerCase()]||{}).ctx??0)>=1e6,t={id:e.id,name:e.labelOverride??e.name,description:ad(e.id),thinking:Hu(e.id),...e.restricted&&wu(e.labelOverride??e.name)};return!s||e.restricted?[t]:[t,{...t,id:`${e.id}[1m]`,description:od,supports_1m_context:!0}]});return Wu.map(e=>({id:e,models:t}))}'
        if old_sd not in c:
            print("  跳过 sd(): 模式未匹配（版本可能已变更）")
        else:
            c = c.replace(old_sd, new_sd, 1)
            changed.append("补丁 sd(): 1M 变体按上下文长度")
    else:
        changed.append("sd() 已补丁")

    # 3. Hu(): 思考强度按 reasoning
    if "MdlMap[e.toLowerCase()]" not in c:
        old_hu = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n)n=ju;'
        old_hu_orig = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n)return;'
        if old_hu in c:
            new_hu = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n){let m=MdlMap[e.toLowerCase()];n=m?m.reasoning?ju:void 0:void 0}if(!n)return;'
            c = c.replace(old_hu, new_hu, 1)
            changed.append("补丁 Hu(): 思考强度按 reasoning")
        elif old_hu_orig in c:
            new_hu = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n){let m=MdlMap[e.toLowerCase()];n=m?m.reasoning?ju:void 0:void 0}if(!n)return;'
            c = c.replace(old_hu_orig, new_hu, 1)
            changed.append("补丁 Hu(): 思考强度按 reasoning（原始守卫版本）")
        else:
            print("  跳过 Hu(): 模式未匹配（版本可能已变更）")
    else:
        changed.append("Hu() 已补丁")

    if changed:
        open(chunk_path, "w", encoding="utf-8").write(c)
    for msg in changed:
        print(f"  {msg}")
    return True


def main():
    resources_dir = find_resources_dir()
    asar_path = os.path.join(resources_dir, "app.asar")
    if not os.path.exists(asar_path):
        print(f"跳过 (app.asar 不存在): {asar_path}")
        return
    if not os.path.exists(MODEL_MAP):
        print(f"跳过 (model-map.json 不存在): {MODEL_MAP}（先运行 generate-model-map.py）")
        return

    tmp = tempfile.mkdtemp(prefix="claude-asar-")
    try:
        run_npx(["extract", asar_path, tmp])
        chunk_path = os.path.join(tmp, CHUNK_REL)
        if not os.path.exists(chunk_path):
            print(f"跳过 (chunk 不存在): {CHUNK_REL}")
            return
        print("=== 修补模型映射 (app.asar) ===")
        if patch_chunk(chunk_path):
            unpacked = asar_path + ".unpacked"
            if os.path.isdir(unpacked):
                shutil.rmtree(unpacked)
            run_npx(["pack", tmp, asar_path, "--unpack", UNPACK_GLOB])
            print("  已重新打包 app.asar（请重新签名，见 llms.txt）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
