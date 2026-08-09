# Claude Desktop 中文本地化

为 Claude Mac 桌面应用提供简体中文和繁体中文翻译，并附带模型映射与运行修复。

## 安装

AI Agent 自动化安装（唯一方式）：根据 llms.txt 汉化本地 Claude Desktop。

版本更新过快，手动安装难以跟进；AI Agent 会按 llms.txt 自动完成翻译、模型映射、重签名与安装。

## 功能

- 全量汉化：Electron 原生界面、Web UI（约 2 万键）、系统菜单，简体 + 繁体
- 模型映射：每次汉化自动拉取 models.dev 的 opencodezen 节点配置，映射模型上下文长度（1M 变体）与思考强度档位
- 运行修复：语言白名单、模型发现恢复、钥匙链弹窗消除

## 目录结构

```
data/    翻译数据与模型映射（en-US.json、model-map.json 等）
scripts/ 汉化与模型映射脚本（apply.py 等）
llms.txt AI Agent 操作指南（完整流程）
```

## 翻译规范

简体用大陆术语（文件/设置/服务器），繁体用台湾术语（檔案/設定/伺服器）；品牌名（Claude、GitHub 等）与技术词（API、MCP 等）保持英文；ICU 语法、HTML 标签、变量插值原样保留。
