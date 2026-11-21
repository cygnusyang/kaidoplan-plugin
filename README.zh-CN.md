# KaidoPlan 多宿主插件

**简体中文** · [English](README.md)

KaidoPlan 提供标准 Agent Skill 和 stdio MCP 配置。插件包放在 `claude-code/`，以兼容已有的 Claude Code 安装路径。

## 安装

先在受支持的设备上安装 KaidoPlan Pro。macOS 上的 Homebrew 软件包提供 `kaidoplan` 和 `kaidoplan-mcp`，宿主进程需要能从 PATH 找到它们。

```sh
brew install cygnusyang/kaidoplan/kaidoplan-cli
```

也可在 KaidoPlan 主工程源码目录运行 `swift build -c release`，使用 `.build/release/KaidoPlanCLI` 和 `.build/release/KaidoPlanMCP` 的绝对路径。Claude Code 启动脚本支持 `KAIDOPLAN_CLI_BIN` 和 `KAIDOPLAN_MCP_BIN`。

| 宿主 | 安装方式 |
|---|---|
| Claude Code | 运行 `claude --plugin-dir /绝对路径/kaidoplan-plugin/claude-code`。参见 [Claude Code 命令和完成钩子](claude-code/README.zh-CN.md)。 |
| Codex | 在仓库根目录运行 `codex plugin marketplace add .` 注册[本地市场](.agents/plugins/marketplace.json)，再运行 `codex plugin add kaidoplan@kaidoplan-local`。个人市场可将同一条目的 `source.path` 改为插件包绝对路径。[Codex 打包文档](https://developers.openai.com/plugins/build/plugins) |
| Cursor | 通过插件市场安装[标准插件包](claude-code/plugin.json)，或按下文分别安装 Skill 和 MCP。[Cursor 插件文档](https://cursor.com/docs/reference/plugins) |
| VS Code / GitHub Copilot | 通过 Agent Plugin 安装标准插件包，或按下文分别安装 Skill 和 MCP。[VS Code 插件文档](https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference) |
| WorkBuddy | 按下文打包 Connector，也可通过客户端添加本地 MCP 并导入技能。[WorkBuddy Connector 文档](https://open.workbuddy.cn/en/docs/connector) |
| Gemini CLI、CodeBuddy 和其他支持 Agent Skills 与 MCP 的宿主 | 按下文分别安装 Skill 和 MCP。 |

### WorkBuddy Connector

从仓库根目录打包，确保连接器文件位于 ZIP 根目录。发布到 WorkBuddy 市场需要审核。

```sh
(cd claude-code && zip -r ../kaidoplan-workbuddy.zip connector-meta.json mcp.json icon.svg skills)
```

本地使用时，在 WorkBuddy 的连接器界面注册 stdio 命令 `kaidoplan-mcp`，参数留空，按提示信任连接器，再在技能界面导入 [KaidoPlan 技能](claude-code/skills/kaidoplan/SKILL.md)。

### 分别安装 Skill 和 MCP

将整个 `claude-code/skills/kaidoplan/` 目录放进宿主的技能目录。在宿主的 MCP 界面或 CLI 注册名为 `kaidoplan` 的 stdio 服务，命令为 `kaidoplan-mcp`，参数留空。宿主无法继承终端 PATH 时，使用二进制的绝对路径。参见[标准 MCP 配置](claude-code/mcp.json)。

```sh
codex mcp add kaidoplan -- kaidoplan-mcp
gemini mcp add kaidoplan kaidoplan-mcp
codebuddy mcp add --scope user kaidoplan -- kaidoplan-mcp
```

安装后，在宿主中确认能够发现技能并列出 KaidoPlan 工具。

## 供其他技能调用

加载[共享技能](claude-code/skills/kaidoplan/SKILL.md)，或按其中的交接约定调用 MCP。调用方技能可写入这样的指令：

> 调用 KaidoPlan 技能执行 `plan`，目标文件为 `/绝对路径/payments.kaido`，需求来自本次交接。返回已保存的任务 ID 和排期冲突。

调用方必须提供确切的目标文件。使用 MCP 时，每次操作前把路径传给 KaidoPlan 的 `project_open` 工具。使用官方 CLI 时，每条项目命令都通过 `--file <绝对路径>` 传入目标。由 KaidoPlan 加载和保存项目，技能通过同一接口回读验证。禁止用编辑器、脚本、Shell 或通用文件工具直接读写 `.kaido` 账本，或创建任务 JSON 文件。WBS 直接作为 MCP 参数传入。KaidoPlan 调用失败时，须报告失败并停止受影响的操作。

这些规则约束插件和技能的调用流程。若宿主还授予 AI 独立的文件访问能力，需通过宿主或操作系统的权限隔离来强制执行。

## WBS 怎么拆（重点）

### 三层结构

```
里程碑（kind=milestone，零工期，对齐外部事件：提测 / 上线 / 评审）
└── 群组（kind=group，只装子节点，不设投入）
    └── 叶子（kind=task，必须有 effortHours，排期与回写的单元）
```

### 叶子判据（四条全中才是叶子）

1. **可独立验收**：一句话说清「做完的标准」，不需要等别的任务一起看；
2. **单人单责**：一个负责人，不需要并行协商；
3. **0.5–3 人日**：低于半天说明拆过头（合并成本 > 管理成本），高于 3 天说明还没拆清；
4. **有明确产出物**：文件、接口、文档、可运行行为之一。

### 投入与工期

- 只填 `effortHours`（人时），排期引擎按 8 小时/人日折算持续时间；
- 群组与里程碑不填投入，完成度由子任务**按投入加权**聚合；
- 不给投入 = 排期不可信、违例检查退化。

### 依赖

只在叶子之间连，格式 `前置ID:类型[:lag]`：

| 类型 | 语义 | 用在哪 |
|---|---|---|
| `fs` | 前置完成后才能开始（默认） | 95% 的场景 |
| `ss` | 与前置同时开始 | 两条并行开发线 |
| `ff` | 与前置同时结束 | 收尾对齐 |
| `sf` | 前置开始后才能结束 | 极少用 |

`lag` 是前导天数，用于「接口冻结后等 2 天才联调」这类现实间隔。

### 反例

| 写法 | 问题 |
|---|---|
| 「开发支付模块」当叶子、投入 80 小时 | 不可验收、无法并行；拆成接口 / 服务端 / 客户端 / 联调 |
| 群组上填投入 | 完成度会双算 |
| 里程碑填 2 天工期 | 里程碑是时间点，不是工作 |
| 依赖连到群组 | 排期只认叶子，连群组语义不明 |
| 两个任务同名 | Claude Code hook 会跳过或误标 |

## 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `command not found` / 找不到 KaidoPlanMCP | 未构建或路径写错 | `swift build -c release`，配置里用绝对路径 |
| MCP 连上但工具报「未打开项目」 | 工具不会读环境变量，需显式路径 | 先 `project_open`，或在规则文件里写死路径 |
| `kaidoplan-mcp: KaidoPlanMCP not found` | 仓库里没有构建产物，`PATH` 上也没有 `kaidoplan-mcp` | `brew install cygnusyang/kaidoplan/kaidoplan-cli`，或构建，或设 `KAIDOPLAN_MCP_BIN` |
| Claude Code 任务完成但没回写 | 标题不唯一 / 缺 `KAIDOPLAN_PROJECT` / 找不到 CLI | 看 stderr 的 `kaidoplan-hook:` 行；设 `KAIDOPLAN_CLI_BIN` |
| 应用与 AI 同时改同一个 `.kaido` | 无自动合并 | 应用会提示重新载入；回写期间关应用 |
| 排期日期差一天 | 输出是 UTC，应用显示本地 | 以应用或 `--json` 的本地日期为准 |
| CLI/MCP 提示「需要 KaidoPlan Pro」（退出码 3） | 没有 license 文件或订阅 | 激活 license 或订阅；见 https://kaidoplan.cygnusyang.top/#pricing |


## 协议

本仓库内容（插件 manifest、MCP 配置、hook 脚本、斜杠命令、包装脚本）以 [MIT 协议](LICENSE) 开源——欢迎 fork、修改、发布你自己的版本；改进欢迎在本仓提 PR。

它调度的 KaidoPlan 应用与 CLI 二进制仍是专有软件，需要有效的 license 或订阅。
