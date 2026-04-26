#!/usr/bin/env python3
"""
Claude Desktop 中文本地化补丁应用脚本

用法:
  python3 apply.py [Resources路径]

默认 Resources 路径: /Applications/Claude.app/Contents/Resources
"""

import json
import os
import re
import sys
import glob


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
        # 格式: "key" = "value";
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
    """查找主 JS 文件（文件名包含 hash，每个版本不同）"""
    pattern = os.path.join(resources_dir, "ion-dist", "assets", "v1", "index-*.js")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    return None


def apply_js_locale_patch(js_path):
    """在 JS 文件中修改语言显示名称"""
    if not js_path or not os.path.exists(js_path):
        print("  跳过 (JS 文件未找到)")
        return False

    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找 localName 生成代码
    old_pattern = "localName:n.formatters.getDisplayNames(t,SEn).of(t)"
    if old_pattern not in content:
        print("  跳过 (未找到 localName 模式，可能版本已变更)")
        return False

    new_code = 'localName:{"zh-CN":"简体中文（中国大陆）","zh-TW":"繁体中文（中国台湾）"}[t]||n.formatters.getDisplayNames(t,SEn).of(t)'
    content = content.replace(old_pattern, new_code)

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


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
            with open(patch_file, "r", encoding="utf-8") as f:
                patch = json.load(f)
            count = apply_json_patch(target_file, patch)
            print(f"  {lang}.json: 更新 {count} 条")

    # 2. lproj Localizable.strings
    print("\n=== 修补 lproj Localizable.strings ===")
    lproj_map = {
        "zh_CN": os.path.join(DATA_DIR, "zh_CN.lproj_Localizable.strings"),
        "zh_TW": os.path.join(DATA_DIR, "zh_TW.lproj_Localizable.strings"),
    }
    for locale, patch_file in lproj_map.items():
        target_file = os.path.join(resources_dir, f"{locale}.lproj", "Localizable.strings")
        if os.path.exists(patch_file):
            count = apply_lproj_patch(target_file, patch_file)
            print(f"  {locale}.lproj/Localizable.strings: 更新 {count} 条")

    # 3. ion-dist i18n JSON
    print("\n=== 修补 ion-dist/i18n JSON ===")
    for lang in ["zh-CN", "zh-TW"]:
        patch_file = os.path.join(DATA_DIR, f"ion-dist-{lang}.json")
        target_file = os.path.join(resources_dir, "ion-dist", "i18n", f"{lang}.json")
        if os.path.exists(patch_file):
            with open(patch_file, "r", encoding="utf-8") as f:
                patch = json.load(f)
            count = apply_json_patch(target_file, patch)
            print(f"  ion-dist/i18n/{lang}.json: 更新 {count} 条")

    # 4. JS locale display name patch
    print("\n=== 修补 JS 语言显示名称 ===")
    js_path = find_index_js(resources_dir)
    js_name = os.path.basename(js_path) if js_path else "未找到"
    print(f"  目标文件: {js_name}")
    if apply_js_locale_patch(js_path):
        print("  已应用语言名称补丁")
    else:
        print("  未应用")

    print("\n完成！请重启 Claude 应用以使更改生效。")


if __name__ == "__main__":
    main()
