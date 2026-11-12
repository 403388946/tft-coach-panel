# TFT Coach Panel（云顶之弈参谋面板）

> 只读截图、人工操作、AI 给建议的本地参谋面板原型。**不是自动代打工具。**

## 项目定位

为《云顶之弈》对局提供辅助参谋：面板读取当前局面（优先本地提取成结构化文本），交给云端大模型结合当前版本 meta 给出经济、买牌、羁绊缺口、装备、站位方面的建议；**所有游戏操作由玩家本人完成**。

P0 面板骨架已落地（Tkinter 标准库实现）：状态 / 海克斯录入、字段锁定、羁绊断点查表、抓帧调用、本地梳理建议、存疑清单标注与分段耗时（抓帧 / 决策）；本地提取层（OCR / 小模型）与云端决策接口在后续阶段接入。

## 合规红线（本项目明确不做）

以下功能本项目**不包含、不规划、不接受 PR 实现**：

- 模拟鼠标键盘、自动买牌 / 刷新 / 升人口 / 走位 / 拖阵；
- 读取游戏进程内存、模块、句柄；Hook、注入、改包；
- 直连客户端本地 API（解析进程命令行端口令牌、自动匹配 / 接受 / 投降 / 强杀进程）；
- 管理员提权、全局快捷键钩子、改写客户端配置；
- 隐藏后台常驻、切虚拟桌面绕过界面。

信息获取只走：本地只读抓帧（窗口自绘优先，黑屏回退屏幕合成画面）+ 公开赛季静态数据 + 玩家手动录入。

> **免责声明**：本项目仅供个人学习与研究使用。使用前请阅读并遵守 Riot Games / 腾讯的用户协议与反作弊规则。使用者自行承担合规责任；本项目作者不对任何账号处罚或损失负责。

## 功能规划

- **P0（MVP）**：轻量侧边栏；调只读抓帧脚本；结构化状态对象 + 手动录入 / 字段锁定；云端对话决策；本地查表标注羁绊断点；存疑字段保守标注。
- **P1**：本地 OCR / 小模型自动填状态；场上棋子身份 / 星级 / 装备识别（局部小图兜底）；目标阵容与站位卡片。
- **P2（可选）**：对手对位建议；本地 agent（羁绊断点复核 + 数据查表 + 服务端二次校验）；面板美化；评估升级为本地 Web 面板或桌面应用。

详细设计见 [`docs/panel-design-lightweight.md`](docs/panel-design-lightweight.md)。

## 混合架构

```
抓帧(只读脚本) → 本地提取层(认字读数, 不出本机) → 结构化 state → 云端决策层 → 建议
```

本地负责把画面读成几十字结构化文本，云端负责判断决策；识别存疑的局部小图再回传云端。纯本地端到端（本地看图 + 本地出建议）不在规划内：小模型不懂版本 meta，识别准确率也不足。

详见 [`docs/architecture-hybrid.md`](docs/architecture-hybrid.md)。

## 目录结构

```
tft-coach-panel/
├── README.md                    # 本文件
├── LICENSE                      # MIT
├── tft-coach-panel.py           # 面板启动入口：python tft-coach-panel.py
├── requirements.txt             # P0 仅标准库，无第三方依赖
├── app/
│   ├── state.py                 # BoardState 结构化状态 + 存疑/锁定 + 局面文本模板
│   ├── traits.py                # 羁绊断点确定性查表（达标 / 差额 / 溢出）
│   ├── capture.py               # 只读抓帧封装（调用 scripts/capture-lol.ps1）
│   ├── decide.py                # 决策接口：本地梳理 + 云端接口预留
│   └── panel.py                 # Tkinter 侧边栏界面与交互流程
├── docs/
│   ├── panel-design-lightweight.md   # A 轻量面板设计稿（界面 / 字段 / 流程 / 分期）
│   ├── architecture-hybrid.md        # 本地提取 + 云端决策混合架构方案
│   ├── coach-manual-s18.md           # S18 参谋手册（阵容 / 节奏 / 开局判断 / 边界）
│   └── references.md                 # 参考项目致谢
├── scripts/
│   └── capture-lol.ps1               # Windows 只读抓帧脚本（PrintWindow 优先，黑屏回退）
└── data/                        # 赛季词表 / 图标素材获取说明（不打包第三方数据）
```

## 运行方式

```powershell
# 推荐 Python 3.13（自带 Tcl/Tk 8.6，标准安装包默认包含）
python tft-coach-panel.py
```

- P0 仅使用 Python 标准库（tkinter / subprocess / threading / dataclasses），无需 `pip install`。
- 面板按钮：**重抓帧**（调用只读脚本抓一帧，显示抓帧耗时）、**生成建议**（本地梳理 + 断点标注，显示决策耗时与存疑清单；决策失败保留上一条建议）、**复制局面文本**（导出结构化局面，贴给云端对话）。
- 决策接口 `app/decide.py` 的 `call_cloud()` 为预留桩，后续接 OpenAI 兼容接口；P0 不联网、不加载本地模型。

### 运行环境与已验证项

- 本机已安装官方 CPython **3.13.15**（用户级目录 `%LOCALAPPDATA%\Programs\Python\Python313`，自带 Tcl/Tk 8.6 与 pip）；面板窗口已验证可实例化（440×760，标题「TFT 参谋面板（P0）」），纯逻辑层无头自检通过。
- 注意：沙箱内嵌的裁剪 Python 缺 `tcl8.6` / `tk8.6` 脚本目录，不能用来弹窗；若命令行 `python` 仍指向该内嵌运行时，请改用完整版 Python 路径，或新开终端让用户 PATH 生效。

### 仍待实测 / 未接入

- 真机对局内抓帧：PrintWindow 在 DX 渲染下是否黑屏（脚本已有黑屏回退 CopyFromScreen），需进真实对局确认。
- 云端决策接口：`call_cloud()` 仍是预留桩，P0 建议为本地确定性梳理，版本 meta 判断暂走「复制局面文本贴云端对话」。

## 赛季与版本口径

- 赛季以客户端实际版本为准（当前基线 S18）；第三方攻略站同名旧赛季条目仅作参考。
- 赛季静态数据（棋子 / 羁绊 / 装备 / 强化符文）通过公开官方静态资源获取，版本更新只替换数据包，不改决策逻辑。

## 收录状态

- **已落地（P0）**：面板骨架代码 `app/` + `tft-coach-panel.py`；只读抓帧脚本 `scripts/capture-lol.ps1`；S18 参谋手册 `docs/coach-manual-s18.md`；方案设计、架构对照与规划文档。
- **待后续阶段**：本地提取层（OCR / 小模型自动填状态）、云端决策接口接入、场上棋子身份 / 星级 / 装备识别；详见面板设计稿分期。

## 致谢与参考项目

设计阶段参考了以下开源项目，在此向原作者致谢；本仓库不复制其代码与数据，详见 [`docs/references.md`](docs/references.md)：

- [TFT-Hextech-Helper](https://github.com/WJZ-P/TFT-Hextech-Helper)
- [TFT_Spider](https://github.com/Jack0Chan/TFT_Spider)
- [TFT-Copilot](https://github.com/ZhongliangGuo/TFT-Copilot)

## 许可

[MIT](LICENSE)。仓库内不打包上述参考项目的代码与数据；若后续引入其模型权重或素材，将在对应目录注明来源与原协议。
