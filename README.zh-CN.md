# 用 AI 智能体做项目：KaidoPlan 接入指南

> **一份条目通吃所有 MCP 宿主**——下表与合并脚本对 Cursor、Gemini CLI、VS Code、WorkBuddy 以及其他任意 stdio 客户端都适用；`tools/list` = 21。

[English](README.md) · **简体中文**

> **正本在主开发仓的 `Plugins/` 目录**（该仓不公开），本仓是 Claude Code 插件的独立安装入口，issue 与 PR 提到本仓即可。

> 面向两种人：① 想让 AI 帮忙拆 WBS、排期、盯进度的人；② 要给某个智能体（Claude Code / Codex / Cursor / Gemini CLI / VS Code / CodeBuddy / WorkBuddy）接上 KaidoPlan 的人。
> 本文走查部分在 KaidoPlan v0.9.1（2026-10-25）用 release 产物实测通过；MCP 契约本身（`initialize` → `protocolVersion 2024-11-05`、`tools/list` → **21 个工具**）于 2026-11-16 在 v3.11.x 上复验。宿主侧配置按各家官方格式给出，边界见文末「验证范围」。

## 兼容性：一个 MCP server，多家宿主通吃

`kaidoplan-mcp` 就是一个普通的 **stdio JSON-RPC MCP server**——没有 SDK、没有框架、没有宿主专属方言。任何支持 stdio MCP 的客户端都能驱动它；插件/hook 只是叠在上面的便利层，不是额外能力：

| 宿主 | 接法 | 配置落点 | 本仓提供的额外件 |
|---|---|---|---|
| Claude Code | MCP，或完整插件 | `.mcp.json` | 插件：3 个斜杠命令 + `TaskCompleted` 回写 hook |
| Codex CLI | MCP | `~/.codex/config.toml` | 规则块写 `AGENTS.md` |
| Cursor | MCP | `~/.cursor/mcp.json` 或 `.cursor/mcp.json` | 规则块写 `AGENTS.md` / `.cursor/rules/` |
| Gemini CLI | MCP | `~/.gemini/settings.json` 或 `.gemini/settings.json` | 规则块写 `GEMINI.md` / `AGENTS.md` |
| VS Code（Copilot agent 模式） | MCP | `.vscode/mcp.json`（工作区）或用户配置 | 规则块写 `AGENTS.md` / `.github/copilot-instructions.md` |
| CodeBuddy | MCP | `.mcp.json` | 规则块写 `CODEBUDDY.md` |
| WorkBuddy | MCP | `~/.workbuddy/mcp.json` | 规则块写 `CODEBUDDY.md` / `AGENTS.md` |
| 其他任何客户端 | stdio MCP | 各家自己的配置文件 | — |

配置文件名与 schema 归各家所有，下面片段按其当前文档给出。本仓库自己实测的只有两件：stdio 探针（§2）与 Claude Code 插件 hook（有测试覆盖）。

## 0. 一句话说清分工

| 角色 | 干什么 | 不干什么 |
|---|---|---|
| AI 智能体 | 读需求、拆任务、估投入、写代码、完成后回写状态 | 不做长期记忆，不维护进度账本 |
| KaidoPlan | 存 WBS 与依赖、算排期、查违例与重要路径、聚合完成度 | 不写代码、不替 AI 做技术判断 |
| 人 | 定边界（起止日期、验收口径）、看甘特与违例、干预 | 不逐条盯任务 |

KaidoPlan 的三个入口同源（共用同一套写路径 `KaidoPlanSession`）：**MCP 工具 21 个**、**CLI 命令**、**macOS 应用**。数据只有一个落点：`.kaido` 单文件（JSON）。AI 走前两个，人走第三个。

## 1. 为什么只有 Claude Code 有插件

插件不是能力，是**桥**。四件套里三件能被 MCP/CLI 取代，只有 hook 不能：

| 组件 | 能否用通用接口替代 | 结论 |
|---|---|---|
| `.mcp.json` | 能（项目级 MCP 配置） | 只省一步手工配置 |
| 斜杠命令 | 能（规则文件里的一段约定） | 便利，非必需 |
| `TaskCompleted` hook | **不能** | 唯一真正值钱的部分 |
| 清单 / 市场分发 | 不能 | 只在对外分发时值钱 |

而 hook 的用途是**桥接 Claude Code 自己的任务系统**（TaskCreate / TaskCompleted）到 KaidoPlan。Codex 没有等价事件；CodeBuddy 的插件格式是 Claude 格式的分叉（清单目录、根变量名都改了）。给它们各做一个壳，收益是「省一次配置」，成本是「永远跟着对方格式改」。

所以本仓库的取舍：

- **Claude Code**：保留完整插件（斜杠命令 + 自动回写 hook），已实测；
- **其余宿主**（Codex / Cursor / Gemini CLI / VS Code / CodeBuddy / WorkBuddy）：不装插件，一份 MCP 配置 + 一段写进规则文件的约定，零维护。

三种接法里，前两步（§2、§3）通用，做完再挑宿主。

## 2. 共用前置：构建 + 建项目

**生产安装（推荐）**——一条命令把 `kaidoplan` 与 `kaidoplan-mcp` 都装到 PATH 上，无需拉取源码：

```bash
brew install cygnusyang/kaidoplan/kaidoplan-cli
```

如果你走的是这条安装路径，下文里的 `"$KAIDOPLAN/.build/release/KaidoPlanCLI"` 一律读作 `kaidoplan`、`"$KAIDOPLAN/.build/release/KaidoPlanMCP"` 一律读作 `kaidoplan-mcp`。

> CLI 与 MCP 属 **KaidoPlan Pro**：两者都需要有效 license 或订阅，否则以退出码 `3` 结束。

**从源码构建**（Swift 5.9+，Xcode 16+）：

```bash
# 1) 改这一行：指向你的 KaidoPlan 仓库
export KAIDOPLAN="$HOME/path/to/KaidoPlan"

# 2) 构建（MCP 与 CLI 两个产物一次出来）
cd "$KAIDOPLAN" && swift build -c release

# 3) 建工作目录和项目文件
mkdir -p "$HOME/Projects/demo" && cd "$HOME/Projects/demo"
"$KAIDOPLAN/.build/release/KaidoPlanCLI" project create "示例项目" \
  --start 2026-11-02 --end 2026-11-20 --file demo.kaido
```

成功输出：

```
已创建项目：52F28B11「示例项目」
已保存：/Users/you/Projects/demo/demo.kaido
格式版本：v1
```

> `--start` / `--end` 是排期引擎的默认边界，超出会报违例。日期一律 `YYYY-MM-DD`。
> CLI 语言按 `--lang <bcp47>` → `KAIDOPLAN_LANG` → 系统语言决定，默认回退简体中文；`--json` 输出与语言无关。

可选：验证 MCP 服务本身（两行，看到 serverInfo 与 tools 即通）：

```bash
printf '%s\n%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
 | "$KAIDOPLAN/.build/release/KaidoPlanMCP" | head -c 400
```

## 3. 共用约定：把这段放进宿主的规则文件

Codex / Cursor 放 `AGENTS.md`，Gemini CLI 放 `GEMINI.md`（或 `AGENTS.md`），CodeBuddy 放 `CODEBUDDY.md`，Claude Code 放 `CLAUDE.md`（都在**项目根目录**）。把路径换成你的真实路径：

```markdown
## KaidoPlan 项目管理

本项目用 KaidoPlan 管理 WBS 与排期，项目文件固定为：/Users/you/Projects/demo/demo.kaido

- 开工前先 task_list 读现状，已有任务不要重复创建。
- 拆解顺序：里程碑 → 群组 → 叶子。叶子必须给 effortHours（按 8 小时/人日估），群组与里程碑不给投入。
- 一个叶子 = 一次可交付、可独立验收的改动；预计超过 3 人日就继续拆。
- 拆完立刻 wbs_import，然后 schedule_compute；violations_list 有输出先报告，不要擅自改期限或依赖。
- 每完成一个任务，必须调用 status_update 把状态置 done（进度自动 100%），不要只改进度数字。
- 任务 ID 接受完整 UUID 或 ≥4 位唯一前缀；前缀不唯一时先列候选让用户选，禁止猜。
- 只建计划不写代码时，明确声明「本次只更新 KaidoPlan 计划」。
```

这段约定是三个宿主**唯一**共用的智能层。要改，只改这里，不要在别处再抄一份。

## 4. Claude Code

### 接法 A：只接 MCP（最简，30 秒）

```bash
cd "$HOME/Projects/demo"
cat > .mcp.json <<EOF
{
  "mcpServers": {
    "kaidoplan": { "command": "$KAIDOPLAN/.build/release/KaidoPlanMCP" }
  }
}
EOF
```

然后 `claude`，首次会提示是否信任该项目的 MCP 服务，同意即可。**这份 `.mcp.json` 与 CodeBuddy 通用**（见 §5），一份配置两个宿主。

### 接法 B：完整插件（斜杠命令 + 自动回写）

```bash
export KAIDOPLAN_PROJECT="$HOME/Projects/demo/demo.kaido"
claude --plugin-dir "$KAIDOPLAN/Plugins/claude-code"
```

| 命令 | 作用 |
|---|---|
| `/kaidoplan plan <需求文档路径或需求描述>` | 读需求 → 建 WBS → 排期 → 列违例 |
| `/kaidoplan done <任务ID 或前缀>` | 标记完成并回报群组完成度 |
| `/kaidoplan status` | 任务表、重要路径、违例汇总 |

插件还注册 `TaskCompleted` hook：Claude Code 任务完成时按**标题精确匹配**找到同名 KaidoPlan 任务并回写 `done`。因此参与回写的标题必须项目内唯一，否则跳过（重名）或误标（跨任务同名）。hook 直写文件，与应用并发编辑会互相覆盖，回写期间建议关掉应用。

## 5. CodeBuddy

**不做插件壳**（格式分叉，收益只是省一次配置）。两步：

```bash
# 方式一：项目级（推荐，与 Claude Code 共用同一份）
cd "$HOME/Projects/demo"
# §4 已建过 .mcp.json 可跳过
cat > .mcp.json <<EOF
{ "mcpServers": { "kaidoplan": { "command": "$KAIDOPLAN/.build/release/KaidoPlanMCP" } } }
EOF

# 方式二：用户级（所有项目可见）
codebuddy mcp add --scope user kaidoplan -- "$KAIDOPLAN/.build/release/KaidoPlanMCP"
```

项目根放 `CODEBUDDY.md`，内容用 §3 那段。启动 `codebuddy` 后首次连接项目级 MCP 需批准；非交互模式加 `--settings '{"enableAllProjectMcpServers": true}'`。

验证：

```bash
codebuddy -p "用 kaidoplan 的 task_list 列出 demo.kaido 的任务，只输出标题和状态"
```

## 6. Codex

Codex 没有斜杠命令、没有可挂的任务完成事件，只有 `config.toml` 和 `AGENTS.md`。所以回写靠**约定**（§3 最后两条），不靠 hook。

```bash
# 1) 注册 MCP → 写入 ~/.codex/config.toml
cat >> ~/.codex/config.toml <<EOF

[mcp_servers.kaidoplan]
command = "$KAIDOPLAN/.build/release/KaidoPlanMCP"
args = []
EOF

# 2) 项目根放 AGENTS.md，内容用 §3 那段
# 3) 在项目目录启动
cd "$HOME/Projects/demo" && codex
```

Codex 里没有 `/kaidoplan plan`，用一句话触发同样流程：

```
按 AGENTS.md 的 KaidoPlan 流程，把 docs/需求.md 拆成 WBS 导入 demo.kaido，
估算投入，然后排期并列出违例。只更新计划，不写代码。
```

任务完成时让它走 CLI（比走 MCP 更可控，也方便终端复核）：

```bash
"$KAIDOPLAN/.build/release/KaidoPlanCLI" status update 3AE8 --status done \
  --file "$HOME/Projects/demo/demo.kaido"
```

> 本机 `codex` CLI 不在 PATH（装的是桌面版），上述 `config.toml` 按其现有 `[mcp_servers.*]` 结构给出；首次使用请确认 `codex` 能列出 kaidoplan 工具。

## 任何 MCP 宿主：同一份条目（Cursor · Gemini CLI · VS Code · WorkBuddy · 其他）

这几家都是 MCP-only：同一个 server、同样 21 个工具、同一段规则块。条目本身不变，变的只有写进哪个文件、顶层键叫什么：

```json
{ "mcpServers": { "kaidoplan": { "command": "kaidoplan-mcp", "args": [], "env": {} } } }
```

| 宿主 | 文件 | 顶层键 | 写入之后 |
|---|---|---|---|
| Cursor | `~/.cursor/mcp.json` 或 `.cursor/mcp.json` | `mcpServers` | 合并写入，不要整文件覆盖 |
| Gemini CLI | `~/.gemini/settings.json` 或 `.gemini/settings.json` | `mcpServers` | `/mcp` 里能看见该 server |
| VS Code（Copilot harness） | 工作区根 `.mcp.json`，或 `~/.copilot/mcp-config.json` | `mcpServers` | 与 Claude Code 共用同一个文件 |
| VS Code（Local harness，已弃用） | `.vscode/mcp.json` | `servers` | 需在 MCP 视图手动启动；harness 2027-02 移除 |
| WorkBuddy | `~/.workbuddy/mcp.json` | `mcpServers` | 点一次**信任** |
| 其他任意 stdio 客户端 | 该客户端自己的配置 | 它自己的键 | 重启后数工具数 = 21 |

一个脚本通吃所有 JSON 型宿主——只替换 `kaidoplan` 这一个键，文件里其他 server 原样保留：

```bash
python3 - "$HOME/.cursor/mcp.json" mcpServers <<'PY'
import json, pathlib, shutil, sys
path, key = pathlib.Path(sys.argv[1]).expanduser(), sys.argv[2]
mcp_bin = shutil.which("kaidoplan-mcp") or "/opt/homebrew/bin/kaidoplan-mcp"
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() else {}
data.setdefault(key, {})["kaidoplan"] = {"command": mcp_bin, "args": [], "env": {}}
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("wrote", path)
PY
```

路径换成表里你那一行；只有已弃用的 VS Code Local harness 才把 `mcpServers` 换成 `servers`。

两个容易踩的点：

- **VS Code 有两套格式。** 现行 Copilot harness 读的是 `mcpServers`——来自工作区根 `.mcp.json`（所以 VS Code、Claude Code、CodeBuddy 可以共用一个文件）或 `~/.copilot/mcp-config.json`。`.vscode/mcp.json` 里的 `servers` 属于旧的 Local harness，已弃用，2027 年 2 月移除。
- **WorkBuddy 不会自动信任。** 新加的条目在你点**信任**之前是不生效的。

上面的表格加上 §3 的规则块就是接入所需的全部内容；本仓的 Claude Code 插件只额外提供斜杠命令与回写 hook。

## 7. WBS 怎么拆（重点）

### 7.1 三层结构

```
里程碑（kind=milestone，零工期，对齐外部事件：提测 / 上线 / 评审）
└── 群组（kind=group，只装子节点，不设投入）
    └── 叶子（kind=task，必须有 effortHours，排期与回写的单元）
```

### 7.2 叶子判据（四条全中才是叶子）

1. **可独立验收**：一句话说清「做完的标准」，不需要等别的任务一起看；
2. **单人单责**：一个负责人，不需要并行协商；
3. **0.5–3 人日**：低于半天说明拆过头（合并成本 > 管理成本），高于 3 天说明还没拆清；
4. **有明确产出物**：文件、接口、文档、可运行行为之一。

### 7.3 投入与工期

- 只填 `effortHours`（人时），排期引擎按 8 小时/人日折算持续时间；
- 群组与里程碑不填投入，完成度由子任务**按投入加权**聚合；
- 不给投入 = 排期不可信、违例检查退化。

### 7.4 依赖

只在叶子之间连，格式 `前置ID:类型[:lag]`：

| 类型 | 语义 | 用在哪 |
|---|---|---|
| `fs` | 前置完成后才能开始（默认） | 95% 的场景 |
| `ss` | 与前置同时开始 | 两条并行开发线 |
| `ff` | 与前置同时结束 | 收尾对齐 |
| `sf` | 前置开始后才能结束 | 极少用 |

`lag` 是前导天数，用于「接口冻结后等 2 天才联调」这类现实间隔。

### 7.5 反例

| 写法 | 问题 |
|---|---|
| 「开发支付模块」当叶子、投入 80 小时 | 不可验收、无法并行；拆成接口 / 服务端 / 客户端 / 联调 |
| 群组上填投入 | 完成度会双算 |
| 里程碑填 2 天工期 | 里程碑是时间点，不是工作 |
| 依赖连到群组 | 排期只认叶子，连群组语义不明 |
| 两个任务同名 | Claude Code hook 会跳过或误标 |

## 8. 一次完整走查（可直接照抄）

```bash
cd "$HOME/Projects/demo"
BIN="$KAIDOPLAN/.build/release/KaidoPlanCLI"

# ⓪ 没有项目就先建一个（已有则跳过，不会覆盖）
[ -f demo.kaido ] || "$BIN" project create "示例项目" \
  --start 2026-11-02 --end 2026-11-20 --file demo.kaido

# ① 写一份 WBS（嵌套 JSON，叶子省略 children 也合法）
cat > wbs.json <<'EOF'
[
  {"title": "支付模块", "kind": "group", "children": [
    {"title": "接口设计", "effortHours": 16},
    {"title": "服务端实现", "effortHours": 40},
    {"title": "客户端接入", "effortHours": 24},
    {"title": "联调验收", "kind": "milestone"}
  ]}
]
EOF

# ② 导入（整棵树一次成型）
"$BIN" wbs import wbs.json --file demo.kaido

# ③ 看清单（跳过也行，④ 用标题自动取前缀）
"$BIN" task list --file demo.kaido
```

输出（前缀以本地为准）：

```
A02505F9 支付模块 [群组] 待办
AFD19693 接口设计 待办 · 投入 16 小时
18352A76 服务端实现 待办 · 投入 40 小时
EF44782F 客户端接入 待办 · 投入 24 小时
33EC0593 联调验收 [里程碑] 待办 · 投入 0 小时 · 持续 0 天
```

```bash
# ④ 连依赖：用标题取前缀，不用手抄 ID
id() { "$BIN" task list --file demo.kaido --json \
  | python3 -c "import json,sys;print([t['id'][:4] for t in json.load(sys.stdin) if t['title']=='$1'][0])"; }

"$BIN" task update "$(id 服务端实现)" --dep "$(id 接口设计):fs" --file demo.kaido
"$BIN" task update "$(id 客户端接入)" --dep "$(id 服务端实现):fs" --file demo.kaido
"$BIN" task update "$(id 联调验收)" --dep "$(id 客户端接入):fs" --file demo.kaido

# ⑤ 排期
"$BIN" schedule compute --file demo.kaido

# ⑥ 重要路径（宽延为 0 的任务链）
"$BIN" schedule path --file demo.kaido

# ⑦ 违例（环、越界、时限冲突）
"$BIN" violations --file demo.kaido

# ⑧ 回写（AI 每完成一个任务做一次）
"$BIN" status update "$(id 接口设计)" --status done --file demo.kaido
```

实测输出要点：

```
已导入 5 个任务
已计算排期：5 个任务
  <前缀> 接口设计  2026-11-01T16:00:00Z → 2026-11-03T16:00:00Z（2 天，ASAP）
  <前缀> 服务端实现 …（依赖生效，紧接接口设计之后）
  <前缀> 客户端接入 …（紧接服务端实现之后）
  <前缀> 联调验收  …（里程碑，零工期，落在链路末端）
重要路径：0 个任务（宽延限制 0 天）
无违例
已回写：<前缀> 接口设计（已完成，进度 100%）
完成度聚合：100%
```

> 「完成度聚合」聚合的是该任务所在子树——叶子就是它自己，所以这里的 100% 表示「这个叶子做完了」，不等于「整个群组做完了」。
> 排期输出是 ISO8601 **UTC**：本地午夜会显示成前一天 16:00Z（东八区）。看日期以 macOS 应用或 `--json` 为准，别拿终端里的 UTC 直接对日历。

## 9. 协作循环

```
人：定边界（起止日期、验收口径）
  ↓
AI：task_list 看现状 → 拆 WBS → wbs_import → schedule_compute → 报违例
  ↓
人：审甘特与违例（macOS 应用），批准或改期限 / 依赖
  ↓
AI：逐任务实现 → status_update done → 群组完成度自动聚合
  ↓
人：看进度与偏差，决定加塞或缩范围
```

两条协作纪律：

- **先看后写**：AI 每次动手前 `task_list`，否则会重复建树；
- **完成即回写**：只改 `progress` 不改 `status`，群组完成度不会动，人看到的进度是假的。

## 10. 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `command not found` / 找不到 KaidoPlanMCP | 未构建或路径写错 | `swift build -c release`，配置里用绝对路径 |
| MCP 连上但工具报「未打开项目」 | 工具不会读环境变量，需显式路径 | 先 `project_open`，或在规则文件里写死路径 |
| `kaidoplan-mcp: KaidoPlanMCP not found` | 仓库里没有构建产物，`PATH` 上也没有 `kaidoplan-mcp` | `brew install cygnusyang/kaidoplan/kaidoplan-cli`，或构建，或设 `KAIDOPLAN_MCP_BIN` |
| Claude Code 任务完成但没回写 | 标题不唯一 / 缺 `KAIDOPLAN_PROJECT` / 找不到 CLI | 看 stderr 的 `kaidoplan-hook:` 行；设 `KAIDOPLAN_CLI_BIN` |
| 应用与 AI 同时改同一个 `.kaido` | 无自动合并 | 应用会提示重新载入；回写期间关应用 |
| 排期日期差一天 | 输出是 UTC，应用显示本地 | 以应用或 `--json` 的本地日期为准 |
| CLI/MCP 提示「需要 KaidoPlan Pro」（退出码 3） | 没有 license 文件或订阅 | 激活 license 或订阅；见 https://kaidoplan.cygnusyang.top/#pricing |

## 11. 验证范围

- **实测通过**（macOS，KaidoPlan v0.8.0 release 产物，2026-10-23）：§2、§4A、§4B、§5 的 KaidoPlan 侧命令，§8 全流程，插件 hook 回写。
- **复验**（2026-11-16，v3.11.x）：stdio MCP 契约——`initialize` 返回 `protocolVersion 2024-11-05`，`tools/list` 返回 **21 个工具**（前四个为 `project_create`、`project_open`、`project_save`、`task_add`）。
- **未实测**：Cursor / Gemini CLI / VS Code / WorkBuddy 的条目——文件名、顶层键与字段集按各家文档（2026-11-16 核对；其中 VS Code 现在有两套格式：Copilot harness 读工作区 `.mcp.json` 或 `~/.copilot/mcp-config.json` 里的 `mcpServers`，而 `.vscode/mcp.json` 的 `servers` 属于已弃用的 Local harness）给出，但本机未在这几个客户端上实际跑通；Codex 桌面版加载 `[mcp_servers.kaidoplan]` 后工具是否即时可见（本机 `codex` CLI 不在 PATH）；CodeBuddy 的 `TaskCompleted` 事件 payload 字段（文档只列事件名未列字段，故未做 CodeBuddy 版 hook）。

## 协议

本仓库内容（插件 manifest、MCP 配置、hook 脚本、斜杠命令、包装脚本）以 [MIT 协议](LICENSE) 开源——欢迎 fork、修改、发布你自己的版本；改进欢迎在本仓提 PR。

它调度的 KaidoPlan 应用与 CLI 二进制仍是专有软件，需要有效的 license 或订阅。
