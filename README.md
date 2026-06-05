# 小喜桌宠 XiLeDi

> 一只生活在 Windows 桌面右下角的喜乐蒂犬（像素风），陪你工作、学习、放空。

[![Status](https://img.shields.io/badge/status-v1.0.0-brightgreen)]() [![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)]() [![Python](https://img.shields.io/badge/python-3.14-blue)]() [![Qt](https://img.shields.io/badge/PySide6-6.11-green)]() [![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## 这是什么

**小喜桌宠** 是一只透明、置顶、像素风的桌面伙伴。它会在桌面巡游、坐下、睡觉，偶尔主动搭话；可以被抚摸、喂食、聊天；也能在你专注学习时锁定睡眠陪你度过番茄钟。

- **轻量**：常驻内存约 100–150 MB，空闲 CPU < 2%，单可执行文件 70 MB
- **可分发**：双击 Inno Setup 中文向导安装，免管理员权限
- **AI 陪聊**：兼容 OpenAI / DeepSeek / 智谱 / 通义 / 月之暗面 / Ollama 六大厂商
- **隐私安全**：API Key 存 Windows 凭据管理器（不写明文配置），用户数据在 `%APPDATA%\XiLeDi\`

---

## 功能一览

| 模块 | 能力 |
|------|------|
| **陪伴** | 10 状态机（idle / walk / sit / sleep / happy / dizzy / peek / eat / hold_bone / fall），自主巡游 + 边界回弹 + 吸边扒墙偶尔探头招呼 |
| **互动** | 左键单击摇尾 / 双击聊天 / 拖动 dizzy + 释放 fall 摔落地 / 右键菜单（抚摸 / 喂食 / 睡觉 / 聊天 / 提醒 / 设置 / 退出）|
| **喂食** | 双食选择（🦴 骨头飞落 + 走过去叼着甩 / 🥣 狗粮直接落脚边低头嚼），结束自动弹反馈气泡 |
| **AI 聊天** | OpenAI 兼容协议，6 厂商预设，流式打字机效果，最近 20 轮历史持久化 |
| **提醒** | HH:MM 增删提醒，到点桌宠原地弹气泡（不抢焦点）|
| **学习陪伴** | 番茄钟模式，小喜锁定睡眠 + 进度环 + 周期鼓励气泡 + 5 分钟警告 + 结束庆祝 |
| **主动搭话** | 时段分类语料 + 频率可调 + 可设休息时间段 |
| **风格统一** | 28 张 AI 生图像素 sprite + 中文像素字体 Fusion Pixel + 像素风 QSS 面板 |

---

## 安装（普通用户）

1. 到 [Releases](https://github.com/prettyYin/-----cc/releases) 下载最新 `XiLeDi-Setup-1.0.0.exe`（74 MB）
2. 双击运行，中文向导一路下一步（默认装到 `%LOCALAPPDATA%\Programs\XiLeDi`，免 UAC）
3. 完成页勾选"立即启动"即可见到小喜出现在桌面右下角

详细使用方式见 [用户手册](docs/用户手册.md)。

> 杀毒软件误报：本版本未做代码签名，可能被部分国产杀软误报。请在杀软白名单里加 `XiLeDi.exe` 即可。

---

## 从源码运行（开发者）

### 环境要求

- Windows 10 / 11（64 位）
- Python 3.14
- 依赖：PySide6 6.11 / openai SDK / keyring / pywin32-ctypes

### 启动

```bash
git clone https://github.com/prettyYin/-----cc.git
cd 小喜桌宠-cc

# 安装依赖
pip install -r requirements.txt

# 双击启动器（或直接 python main.py）
启动小喜.bat
```

右键桌宠 → "退出小喜" 即可结束进程。

### 自己打包

```bash
# 1. 生成应用图标（一次性）
python build/make_ico.py

# 2. PyInstaller 打 onefile exe
pyinstaller --clean build/pet.spec --distpath build/dist --workpath build/build

# 3. Inno Setup 编译中文向导安装包（需先装 Inno Setup 6）
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" build/installer.iss
# 产出：build/Output/XiLeDi-Setup-1.0.0.exe
```

Inno Setup 中文语言包需另外下载 [ChineseSimplified.isl](https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Unofficial/ChineseSimplified.isl) 放到 Inno Setup 安装目录的 `Languages/` 下。

---

## 项目结构

```
小喜桌宠-cc/
├── main.py                       # 入口
├── 启动小喜.bat                  # 单实例锁启动器
├── requirements.txt
├── src/
│   ├── ai/                       # AI 客户端（流式 QThread + 6 厂商预设 + 小喜人设）
│   ├── core/                     # 配置 / 路径 / 字体 / 提醒 / 番茄钟 / 主动搭话 / 凭据 / 音效
│   ├── pet/                      # 桌宠窗口 / 状态机 / 动画器 / 行为调度 / 喂食 / 占位图
│   ├── ui/                       # 聊天面板 / 设置面板 / 右键菜单 / 气泡 / 粒子 / 托盘 / 进度环
│   └── assets/
│       ├── sprites/              # 10 个状态共 40+ 帧像素 sprite
│       ├── fonts/                # Fusion Pixel 中文像素字体
│       ├── data/                 # 30+ 条主动搭话语料
│       └── icons/                # 应用图标 + UI 图标
├── build/
│   ├── make_ico.py               # 一次性脚本：sprite → 多尺寸 .ico
│   ├── pet.spec                  # PyInstaller spec
│   └── installer.iss             # Inno Setup 中文向导脚本
├── docs/                         # 治理文档（需求规格 / 技术架构 / 编码规范 / 资源规范 / 美术素材清单 / 开发流程 / 里程碑与验收标准 / 用户手册）
└── dev-log/                      # 按日 dev-log（追溯每个里程碑的决策与翻车记录）
```

---

## 里程碑

| ID | 名称 | 状态 | 日期 |
|----|------|------|------|
| M1 | 骨架（透明 / 拖动 / 单实例 / 启动器） | 完成 | 2026-05-23 |
| M1.5 | 治理体系（CLAUDE.md + docs/ + dev-log/） | 完成 | 2026-05-23 |
| M2 | 动画（6 状态机 + 自主巡游 + 边界回弹） | 完成 | 2026-05-23 |
| M3 | 互动（右键菜单 + 抚摸 / 喂食 + 系统托盘 + 设置面板） | 完成 | 2026-05-23 |
| M4 | AI + 提醒（6 厂商流式对话 + cron 气泡提醒） | 完成 | 2026-05-23 |
| M4.5 | 像素风格化（28 张 sprite + 像素字体 + 像素 QSS） | 完成 | 2026-05-25 |
| M4.6 | 主动陪伴 + 学习陪伴（番茄钟 + 锁定睡眠 + 鼓励气泡） | 完成 | 2026-05-25 |
| M4.7 | Key 安全（keyring 凭据管理器 + 历史保留可见） | 完成 | 2026-05-25 |
| M4.8 | 美术与互动升级（吸边 / 双食 / 咀嚼 / 拎脖） | 完成 | 2026-05-26 |
| M4.9 | 互动打磨（4 轮迭代覆盖 5 bug + 4 体验 + 美术升级） | 完成 | 2026-05-26 |
| M5 | 打包分发（PyInstaller exe 70MB + Inno Setup 安装包 74MB + 用户手册） | 完成 | 2026-05-26 |

完整验收记录见 [docs/里程碑与验收标准.md](docs/里程碑与验收标准.md)。

---

## 文档索引

| 任务类型 | 文档 |
|----------|------|
| 我是用户，想用小喜 | [docs/用户手册.md](docs/用户手册.md) |
| 我想了解功能边界 | [docs/需求规格.md](docs/需求规格.md) |
| 我想看模块怎么搭的 | [docs/技术架构.md](docs/技术架构.md) |
| 我要给项目写代码 | [docs/编码规范.md](docs/编码规范.md) + [CLAUDE.md](CLAUDE.md) |
| 我要补美术素材 | [docs/资源规范.md](docs/资源规范.md) + [docs/美术素材清单.md](docs/美术素材清单.md) |
| 我要本地启停 / 自测 | [docs/开发流程.md](docs/开发流程.md) |
| 我想看每天做了啥 | [dev-log/](dev-log/) |

---

## 技术栈

- **GUI**：PySide6 6.11（Qt for Python）
- **AI**：openai SDK（兼容 OpenAI 协议）+ 自研 QThread 流式封装
- **凭据**：keyring + pywin32-ctypes（Windows Credential Manager）
- **配置**：JSON 持久化到 `%APPDATA%\XiLeDi\config.json`
- **打包**：PyInstaller 6.x onefile + Inno Setup 6 中文向导
- **资源**：28 张 AI 生图像素 sprite + Fusion Pixel 中文像素字体

---

## 致谢

- **字体**：[TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font) — Fusion Pixel 中文像素字体
- **像素 sprite**：作者使用 AI 生图工具按 [docs/美术素材清单.md](docs/美术素材清单.md) 的 prompts 生成
- **Inno Setup 中文语言包**：[jrsoftware/issrc 社区维护](https://github.com/jrsoftware/issrc/blob/main/Files/Languages/Unofficial/ChineseSimplified.isl)

---

## 许可证

MIT License — 自由使用、修改、分发。

---

希望小喜能陪你度过每一段忙碌或闲适的时光 🐾
