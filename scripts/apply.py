#!/usr/bin/env python3
"""
Claude Desktop 中文本地化补丁应用脚本

用法:
  python3 apply.py [Resources路径]

默认 Resources 路径: /Applications/Claude.app/Contents/Resources

如果需要处理 SIP 保护（macOS 26+），先手动复制 app 到临时目录再运行：
  cp -R /Applications/Claude.app /tmp/Claude_Backup.app
  python3 apply.py /tmp/Claude_Backup.app/Contents/Resources
  # 然后用管理员权限替换回 /Applications
"""

import json
import os
import re
import sys
import glob
import shutil


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")


def find_resources_dir():
    """查找 Resources 目录"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    default = "/Applications/Claude.app/Contents/Resources"
    if os.path.isdir(default):
        return default
    print("错误: 未找到 Resources 目录，请手动指定路径")
    sys.exit(1)


def copy_json_file(src, dst):
    """直接复制 JSON 文件（用于创建新文件或完全覆盖）"""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def apply_json_patch(target_path, patch_data):
    """将翻译数据合并到目标 JSON 文件（仅更新已存在的 key）"""
    if not os.path.exists(target_path):
        print(f"  跳过 (文件不存在): {target_path}")
        return 0

    with open(target_path, "r", encoding="utf-8") as f:
        target = json.load(f)

    count = 0
    for key, value in patch_data.items():
        if key in target and target[key] != value:
            target[key] = value
            count += 1

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(target, f, ensure_ascii=False, indent=2)

    return count


def create_i18n_from_en(resources_dir, lang, patch_data):
    """基于 en-US.json 创建新的 i18n 文件并应用翻译"""
    en_path = os.path.join(resources_dir, "ion-dist", "i18n", "en-US.json")
    target_path = os.path.join(resources_dir, "ion-dist", "i18n", f"{lang}.json")

    if os.path.exists(target_path):
        return apply_json_patch(target_path, patch_data)

    if not os.path.exists(en_path):
        print(f"  跳过 (en-US.json 不存在): {en_path}")
        return 0

    with open(en_path, "r", encoding="utf-8") as f:
        target = json.load(f)

    count = 0
    for k in target:
        if k in patch_data:
            target[k] = patch_data[k]
            count += 1

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(target, f, ensure_ascii=False, indent=2)

    return count


def apply_lproj_patch(target_path, patch_path):
    """应用 Localizable.strings 补丁"""
    if not os.path.exists(target_path):
        print(f"  跳过 (文件不存在): {target_path}")
        return 0

    with open(patch_path, "r", encoding="utf-8") as f:
        patch_lines = f.read().strip().split("\n")

    with open(target_path, "r", encoding="utf-8") as f:
        target_content = f.read()

    count = 0
    for line in patch_lines:
        line = line.strip()
        if not line or line.startswith("/*"):
            continue
        match = re.match(r'^"(.+?)"\s*=\s*"(.+?)"\s*;', line)
        if match:
            key, value = match.group(1), match.group(2)
            pattern = f'"{key}" = ".*?";'
            new_line = f'"{key}" = "{value}";'
            if re.search(pattern, target_content):
                target_content = re.sub(pattern, new_line, target_content)
                count += 1

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(target_content)

    return count


def find_index_js(resources_dir):
    """查找 index-*.js 文件（文件名包含 hash，每个版本不同）"""
    pattern = os.path.join(resources_dir, "ion-dist", "assets", "v1", "index-*.js")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def find_vendor_locale_js(resources_dir):
    """查找 vendor locale 文件 c4b350ac1-*.js（文件名包含 hash）"""
    pattern = os.path.join(resources_dir, "ion-dist", "assets", "v1", "c4b350ac1-*.js")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def apply_js_whitelist_patch(resources_dir):
    """在 vendor locale JS 文件中修补语言白名单"""
    js_path = find_vendor_locale_js(resources_dir)
    if not js_path or not os.path.exists(js_path):
        print("  跳过 (vendor locale JS 文件未找到)")
        return

    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_whitelist = '["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID"]'
    new_whitelist = '["en-US","de-DE","fr-FR","ko-KR","ja-JP","es-419","es-ES","it-IT","hi-IN","pt-BR","id-ID","zh-CN","zh-TW"]'

    if old_whitelist in content:
        content = content.replace(old_whitelist, new_whitelist)
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  已应用语言白名单补丁 ({os.path.basename(js_path)})")
    else:
        print("  跳过白名单 (模式未匹配，可能已补丁或版本变更)")


def apply_js_localname_patch(resources_dir):
    """在 index-*.js 中修补语言显示名称"""
    js_path = find_index_js(resources_dir)
    if not js_path or not os.path.exists(js_path):
        print("  跳过 (index JS 文件未找到)")
        return

    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    patterns = [
        # 新版 Vite 构建
        ('localName:s.formatters.getDisplayNames(t,gNt).of(t)',
         'localName:{"zh-CN":"简体中文（中国大陆）","zh-TW":"繁体中文（中国台湾）"}[t]||s.formatters.getDisplayNames(t,gNt).of(t)'),
        # 旧版模式（兼容）
        ('localName:n.formatters.getDisplayNames(t,SEn).of(t)',
         'localName:{"zh-CN":"简体中文（中国大陆）","zh-TW":"繁体中文（中国台湾）"}[t]||n.formatters.getDisplayNames(t,SEn).of(t)'),
    ]

    patched = False
    for old_pattern, new_code in patterns:
        if old_pattern in content:
            content = content.replace(old_pattern, new_code)
            patched = True
            print(f"  已应用语言显示名称补丁 ({os.path.basename(js_path)})")
            break

    if not patched:
        print("  跳过显示名称 (模式未匹配，可能已补丁或版本变更)")
        return

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)


def copy_i18n_to_dynamic(resources_dir):
    """将 zh-CN/zh-TW 复制到 dynamic 目录"""
    dynamic_dir = os.path.join(resources_dir, "ion-dist", "i18n", "dynamic")
    for lang in ["zh-CN", "zh-TW"]:
        src = os.path.join(resources_dir, "ion-dist", "i18n", f"{lang}.json")
        dst = os.path.join(dynamic_dir, f"{lang}.json")
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  dynamic/{lang}.json: 已复制")


def main():
    resources_dir = find_resources_dir()
    print(f"Resources 目录: {resources_dir}")
    print()

    # 1. Root level JSON
    print("=== 修补 Root level JSON ===")
    for lang in ["zh-CN", "zh-TW"]:
        patch_file = os.path.join(DATA_DIR, f"root-{lang}.json")
        target_file = os.path.join(resources_dir, f"{lang}.json")
        if os.path.exists(patch_file):
            copy_json_file(patch_file, target_file)
            with open(patch_file, "r", encoding="utf-8") as f:
                patch = json.load(f)
            print(f"  {lang}.json: 写入 {len(patch)} 条")

    # 2. lproj Localizable.strings
    print("\n=== 修补 lproj Localizable.strings ===")
    lproj_map = {
        "zh_CN": os.path.join(DATA_DIR, "zh_CN.lproj_Localizable.strings"),
        "zh_TW": os.path.join(DATA_DIR, "zh_TW.lproj_Localizable.strings"),
    }
    for locale, patch_file in lproj_map.items():
        target_file = os.path.join(resources_dir, f"{locale}.lproj", "Localizable.strings")
        if os.path.exists(patch_file):
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            shutil.copy2(patch_file, target_file)
            print(f"  {locale}.lproj/Localizable.strings: 已覆盖")

    # 3. ion-dist i18n JSON
    print("\n=== 修补 ion-dist/i18n JSON ===")
    for lang in ["zh-CN", "zh-TW"]:
        patch_file = os.path.join(DATA_DIR, f"ion-dist-{lang}.json")
        if os.path.exists(patch_file):
            with open(patch_file, "r", encoding="utf-8") as f:
                patch = json.load(f)
            count = create_i18n_from_en(resources_dir, lang, patch)
            target_file = os.path.join(resources_dir, "ion-dist", "i18n", f"{lang}.json")
            if os.path.exists(target_file):
                print(f"  ion-dist/i18n/{lang}.json: 更新 {count} 条")
            overrides_src = os.path.join(DATA_DIR, f"ion-dist-{lang}.overrides.json")
            overrides_dst = os.path.join(resources_dir, "ion-dist", "i18n", f"{lang}.overrides.json")
            if os.path.exists(overrides_src):
                shutil.copy2(overrides_src, overrides_dst)

    # 4. 复制到 dynamic 目录
    print("\n=== 复制到 dynamic 目录 ===")
    copy_i18n_to_dynamic(resources_dir)

    # 5. JS 语言白名单补丁 (c4b350ac1-*.js)
    print("\n=== 修补 JS 语言白名单 ===")
    apply_js_whitelist_patch(resources_dir)

    # 6. JS 语言显示名称补丁 (index-*.js)
    print("\n=== 修补 JS 语言显示名称 ===")
    apply_js_localname_patch(resources_dir)

    print("\n完成！请重启 Claude 应用以使更改生效。")


if __name__ == "__main__":
    main()
