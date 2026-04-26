# Claude Desktop 中文本地化补丁

为 Claude Mac 桌面应用提供完整的简体中文和繁体中文翻译。

## 修改的文件

| 文件 | 用途 |
|------|------|
| `Resources/zh-CN.json` | Electron 原生界面（简体中文） |
| `Resources/zh-TW.json` | Electron 原生界面（繁体中文） |
| `Resources/zh_CN.lproj/Localizable.strings` | macOS 系统菜单（简体中文） |
| `Resources/zh_TW.lproj/Localizable.strings` | macOS 系统菜单（繁体中文） |
| `Resources/ion-dist/i18n/zh-CN.json` | Web UI 翻译（简体中文） |
| `Resources/ion-dist/i18n/zh-TW.json` | Web UI 翻译（繁体中文） |
| `Resources/ion-dist/assets/v1/index-*.js` | 语言显示名称 |

## 安装与使用

### 方法一：AI Agent 自动化安装（推荐）

请使用 AI agent 自动化安装，理论可支持所有版本的 Claude Desktop。

### 方法二：手动安装

```bash
cd /Applications/Claude.app/Contents/Resources/claude-desktop-chinese
python3 scripts/apply.py
```

然后重启 Claude 应用。

## 注意事项

- `ion-dist/assets/v1/index-*.js` 的文件名包含 hash，每个版本不同
- i18n 的 key 是 hash 值，可能随版本更新而变化
- 翻译数据以 `data/` 目录中的 JSON 文件为准
- `apply.py` 仅更新目标文件中已存在的 key，不会添加新 key
- 版本更新后可能需要重新执行补丁

## 目录结构

```
claude-desktop-chinese/
├── README.md
├── llms.txt              # AI 指导文档
├── data/
│   ├── root-zh-CN.json   # Electron 原生界面翻译
│   ├── root-zh-TW.json
│   ├── ion-dist-zh-CN.json  # Web UI 翻译
│   ├── ion-dist-zh-TW.json
│   ├── ion-dist-zh-CN.overrides.json
│   ├── ion-dist-zh-TW.overrides.json
│   ├── zh_CN.lproj_Localizable.strings  # macOS 系统菜单
│   └── zh_TW.lproj_Localizable.strings
└── scripts/
    └── apply.py           # 补丁应用脚本
```

## 翻译规范

### 简体中文 → 繁体中文（台湾）术语对照

| 简体 | 繁体 | 简体 | 繁体 |
|------|------|------|------|
| 文件 | 檔案 | 项目 | 專案 |
| 设置 | 設定 | 插件 | 外掛 |
| 扩展程序 | 擴充功能 | 仓库 | 存放庫 |
| 市场 | 市集 | 服务器 | 伺服器 |
| 会话 | 工作階段 | 禁用 | 停用 |
| 默认 | 預設 | 自定义 | 自訂 |
| 黑名单 | 封鎖清單 | 白名单 | 允許清單 |
| 应用 | 應用程式 | 保存 | 儲存 |
| 导出 | 匯出 | 导入 | 匯入 |
| 账号 | 帳號 | 搜索 | 搜尋 |
| 筛选 | 篩選 | 创建 | 建立 |
| 池 | 集區 | 例程 | 常式 |
| 演示文稿 | 簡報 | 工件 | 構件 |
| 记忆 | 記憶 | 归档 | 封存 |
| 终端 | 終端機 | 连接 | 連線 |
| 评论 | 留言 | 照片 | 相片 |

### 不翻译的术语

- 品牌名: Claude, GitHub, Slack, Google, Notion, Linear, Microsoft, Stripe, Canva, Cowork 等
- 技术术语: API, URL, SSH, SCIM, SSO, CLI, PR, MCP, Webhook, Issue, token
- 文件名/路径: .claude, metadata.xml, SKILL.md 等
- ICU 语法: `{count, plural, one {...} other {...}}`
- HTML 标签: `<code>`, `<link>`, `<terms>`, `<b>` 等
- 变量插值: `{name}`, `{error}` 等
