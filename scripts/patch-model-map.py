#!/usr/bin/env python3
"""
将 data/model-map.json 嵌入 app.asar（模型上下文长度 + 思考强度映射）。

用法:
  python3 patch-model-map.py [Resources路径]

默认 Resources 路径: /Applications/Claude.app/Contents/Resources

补丁内容（index.chunk-w2M3Ll-M.js）:
  1. 注入 var MdlMap=JSON.parse("...")  （models.dev 紧凑映射）
  2. Hu(): 思考强度由映射 reasoning 决定 → 无目录元数据时回退 ju
  3. sd(): 保持原版，不生成 [1m] 变体（若存在变体生成补丁则还原）

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
PRE_REL = os.path.join(".vite", "build", "index.pre.js")
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


def patch_chunk(chunk_path, pre_path):
    changed = []

    # 0. safeStorage 补丁：永不触碰钥匙链（消灭「请求钥匙链」弹窗）
    pre = open(pre_path, "r", encoding="utf-8").read()
    anchor = 'let E=require("electron");E=u(E);'
    if anchor in pre and "safeStorage.isEncryptionAvailable=()=>!1" not in pre:
        patch = anchor + 'E.safeStorage.isEncryptionAvailable=()=>!1;E.safeStorage.encryptString=e=>Buffer.from("\\x00PLAIN:"+e,"utf8");E.safeStorage.decryptString=e=>{let t=Buffer.from(e).toString("utf8");return t.startsWith("\\x00PLAIN:")?t.slice(7):(()=>{throw new Error("safeStorage disabled")})()};'
        pre = pre.replace(anchor, patch, 1)
        open(pre_path, "w", encoding="utf-8").write(pre)
        changed.append("补丁 safeStorage: 禁用钥匙链（明文存储回退）")
    elif "safeStorage.isEncryptionAvailable=()=>!1" in pre:
        changed.append("safeStorage 已补丁")

    c = open(chunk_path, "r", encoding="utf-8").read()

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

    # 2. sd(): 1M 模型只生成 [1m] 变体（不显示变体前的基础条目）
    variant_only = 'function sd(e){let t=e.models.flatMap(e=>{let s=!!e.supports1m||((MdlMap[e.id.toLowerCase()]||{}).ctx??0)>=1e6,t={id:e.id,name:e.labelOverride??e.name,description:ad(e.id),thinking:Hu(e.id),...e.restricted&&wu(e.labelOverride??e.name)};return!s||e.restricted?[t]:[{...t,id:`${e.id}[1m]`,description:od,supports_1m_context:!0}]});return Wu.map(e=>({id:e,models:t}))}'
    old_variant = 'function sd(e){let t=e.models.flatMap(e=>{let s=!!e.supports1m||((MdlMap[e.id.toLowerCase()]||{}).ctx??0)>=1e6,t={id:e.id,name:e.labelOverride??e.name,description:ad(e.id),thinking:Hu(e.id),...e.restricted&&wu(e.labelOverride??e.name)};return!s||e.restricted?[t]:[t,{...t,id:`${e.id}[1m]`,description:od,supports_1m_context:!0}]});return Wu.map(e=>({id:e,models:t}))}'
    original_sd = 'function sd(e){let t=e.models.flatMap(e=>{let t={id:e.id,name:e.labelOverride??e.name,description:ad(e.id),thinking:Hu(e.id),...e.restricted&&wu(e.labelOverride??e.name)};return!e.supports1m||e.restricted?[t]:[t,{...t,id:`${e.id}[1m]`,description:od,supports_1m_context:!0}]});return Wu.map(e=>({id:e,models:t}))}'
    if variant_only in c:
        changed.append("sd() 已补丁（仅 [1m] 变体）")
    elif old_variant in c:
        c = c.replace(old_variant, variant_only, 1)
        changed.append("sd(): 改为仅 [1m] 变体")
    elif original_sd in c:
        c = c.replace(original_sd, variant_only, 1)
        changed.append("sd(): 仅 [1m] 变体（按映射 ctx）")
    else:
        print("  跳过 sd(): 模式未匹配（版本可能已变更）")

    # 3. Hu(): 思考强度按映射 effort 档位匹配
    if "MdlMap[e.toLowerCase()]" not in c:
        new_hu_tail = 'if(!n){let m=MdlMap[e.toLowerCase()];if(m){if(m.effort&&m.effort.length){let f=m.effort;n={effortLevels:f,recommended:f[Math.floor((f.length-1)/2)]}}else if(m.reasoning){n=ju}}}'
        old_hu = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n)n=ju;'
        old_hu_orig = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n)return;'
        old_hu_map = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);if(!n){let m=MdlMap[e.toLowerCase()];n=m?m.reasoning?ju:void 0:void 0}'
        prefix = 'function Hu(e){let t=ou(e.toLowerCase()),n=Mu[t]??(Nu.test(t)?ju:void 0);'
        if old_hu in c:
            c = c.replace(old_hu, prefix + new_hu_tail + 'if(!n)return;', 1)
            changed.append("补丁 Hu(): 思考强度按 effort 档位")
        elif old_hu_orig in c:
            c = c.replace(old_hu_orig, prefix + new_hu_tail + 'if(!n)return;', 1)
            changed.append("补丁 Hu(): 思考强度按 effort 档位（原始守卫版本）")
        elif old_hu_map in c:
            c = c.replace(old_hu_map, prefix + new_hu_tail, 1)
            changed.append("升级 Hu(): 按 effort 档位匹配")
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
        pre_path = os.path.join(tmp, PRE_REL)
        if not os.path.exists(chunk_path):
            print(f"跳过 (chunk 不存在): {CHUNK_REL}")
            return
        print("=== 修补模型映射 (app.asar) ===")
        if patch_chunk(chunk_path, pre_path):
            unpacked = asar_path + ".unpacked"
            if os.path.isdir(unpacked):
                shutil.rmtree(unpacked)
            run_npx(["pack", tmp, asar_path, "--unpack", UNPACK_GLOB])
            print("  已重新打包 app.asar（请重新签名，见 llms.txt）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
