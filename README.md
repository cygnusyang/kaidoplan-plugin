# KaidoPlan for AI agents

**English** · [简体中文](README.zh-CN.md)

KaidoPlan packages a standard Agent Skill and a stdio MCP server definition. The package lives in `claude-code/` so existing Claude Code installs keep working.

## Install

Install KaidoPlan Pro on a supported machine. The macOS Homebrew package provides both `kaidoplan` and `kaidoplan-mcp`. Make sure the host process can find the binaries on its PATH.

```sh
brew install cygnusyang/kaidoplan/kaidoplan-cli
```

Builds from the main KaidoPlan source checkout can also supply the binaries. Run `swift build -c release` there and use the absolute paths to `.build/release/KaidoPlanCLI` and `.build/release/KaidoPlanMCP`. For Claude Code, the launchers honor `KAIDOPLAN_CLI_BIN` and `KAIDOPLAN_MCP_BIN`.

| Host | Installation |
|---|---|
| Claude Code | Run `claude --plugin-dir /absolute/path/to/kaidoplan-plugin/claude-code`. See the [Claude Code commands and completion hook](claude-code/README.md). |
| Codex | From this checkout run `codex plugin marketplace add .` to register its [local marketplace](.agents/plugins/marketplace.json), then install `kaidoplan@kaidoplan-local` with `codex plugin add kaidoplan@kaidoplan-local`. For a personal marketplace, point the same entry's `source.path` at the absolute package path. [Codex packaging docs](https://developers.openai.com/plugins/build/plugins) |
| Cursor | Import the [portable plugin](claude-code/plugin.json) through your plugin marketplace, or use the Skill + MCP setup below. [Cursor plugin docs](https://cursor.com/docs/reference/plugins) |
| VS Code / GitHub Copilot | Install the portable package using the host's agent plugin support, or use the Skill + MCP setup below. [VS Code plugin docs](https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference) |
| WorkBuddy | Package the Connector as shown below and load it through WorkBuddy's connector workflow. For local setup, register a stdio connector and import the shared skill. [WorkBuddy connector docs](https://open.workbuddy.cn/en/docs/connector) |
| Gemini CLI, CodeBuddy, other Agent Skills + MCP hosts | Install the skill and register the stdio server separately, as shown below. |

### WorkBuddy Connector

From the checkout root, build the package with the connector files at the ZIP root. WorkBuddy's marketplace requires review before publication.

```sh
(cd claude-code && zip -r ../kaidoplan-workbuddy.zip connector-meta.json mcp.json icon.svg skills)
```

For local setup, register command `kaidoplan-mcp` with no arguments in WorkBuddy's Connectors UI, trust it if prompted, and import the [KaidoPlan skill](claude-code/skills/kaidoplan/SKILL.md) through the Skills UI.

### Skill + MCP setup

Install the entire `claude-code/skills/kaidoplan/` directory in the host's skills location. Use the host's MCP UI or CLI to register a stdio server named `kaidoplan` with command `kaidoplan-mcp` and no arguments. Use the absolute binary path if the host does not inherit your shell's PATH. The [portable MCP definition](claude-code/mcp.json) shows the server entry.

```sh
codex mcp add kaidoplan -- kaidoplan-mcp
gemini mcp add kaidoplan kaidoplan-mcp
codebuddy mcp add --scope user kaidoplan -- kaidoplan-mcp
```

After installation, verify that the host discovers the skill and lists KaidoPlan's tools.

## Call from another skill

Load [the shared skill](claude-code/skills/kaidoplan/SKILL.md) or follow its handoff contract and invoke the MCP tools. Example instruction in a calling skill:

> Delegate to the KaidoPlan skill with operation `plan`, project path `/absolute/path/to/payments.kaido`, and the requirements from this handoff. Return the saved task IDs and schedule violations.

The caller must supply the exact target file. With MCP, pass the path to KaidoPlan’s `project_open` tool before each operation. With the official CLI, pass it as `--file <absolute-path>` on every project command. KaidoPlan loads and saves the project, and the skill verifies affected tasks through the same interface. Agents must never use generic file tools, scripts, or shell commands to read or edit the `.kaido` ledger or create JSON task files. WBS data goes into MCP arguments in memory. If KaidoPlan fails, report the failure and stop the affected operation.

This contract governs plugin and skill usage. Enforcing it against an agent with independent filesystem access also requires restricting that access in the host or OS.

## How to break down a WBS (the important part)

### Three levels

```
milestone (kind=milestone, zero duration, aligned to an external event: test hand-off / release / review)
└── group (kind=group, holds children only, no effort)
    └── leaf (kind=task, must carry effortHours; the unit of scheduling and write-back)
```

### Leaf criteria (a leaf only counts if all four hold)

1. **Acceptable on its own**: one sentence states "what done means"; nothing else has to be finished first to judge it;
2. **One owner, one responsibility**: a single person accountable, no parallel negotiation needed;
3. **0.5–3 person-days**: under half a day means you over-split (merge cost exceeds management cost); over 3 days means it is not broken down yet;
4. **A concrete output**: a file, an interface, a document, or an observable behaviour.

### Effort and duration

- Fill in `effortHours` only (person-hours); the engine converts at 8 hours per person-day;
- Groups and milestones carry no effort; their progress is **effort-weighted** from their children;
- No effort means the schedule cannot be trusted and violation checking degrades.

### Dependencies

Connect leaves only, in the form `predecessorID:type[:lag]`:

| Type | Meaning | Where it is used |
|---|---|---|
| `fs` | successor starts after the predecessor finishes (default) | 95% of cases |
| `ss` | both start together | two parallel development lines |
| `ff` | both finish together | aligning wrap-up work |
| `sf` | successor finishes only after the predecessor starts | rarely used |

`lag` is a lead time in days, for real gaps like "integration starts 2 days after the API freezes".

### Anti-patterns

| What people write | Why it is wrong |
|---|---|
| "Build the payment module" as a leaf with 80 hours | Not acceptable, not parallelisable; split into API / server / client / integration |
| Effort on a group | Progress gets counted twice |
| A milestone with a 2-day duration | A milestone is a point in time, not work |
| A dependency pointing at a group | The engine only honours leaves; group dependencies are ambiguous |
| Two tasks with the same title | The Claude Code hook will skip or mis-mark |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found` / KaidoPlanMCP not found | Not built, or the path is wrong | `swift build -c release`, and use absolute paths in the config |
| MCP connected but tools say "no project open" | Tools do not read environment variables; they need an explicit path | Call `project_open` first, or hard-code the path in the rules file |
| `kaidoplan-mcp: KaidoPlanMCP not found` | Neither a build in the checkout nor `kaidoplan-mcp` on `PATH` | `brew install cygnusyang/kaidoplan/kaidoplan-cli`, build, or set `KAIDOPLAN_MCP_BIN` |
| A Claude Code task completed but nothing was written back | Title not unique / `KAIDOPLAN_PROJECT` missing / CLI not found | Read the `kaidoplan-hook:` lines on stderr; set `KAIDOPLAN_CLI_BIN` |
| App and AI editing the same `.kaido` | No automatic merge | The app offers to reload; close the app during write-back |
| Scheduled dates off by one day | Output is UTC, the app shows local time | Trust the app or the local dates in `--json` |
| CLI/MCP says "requires KaidoPlan Pro" (exit code 3) | No license file or subscription | Activate a license or subscribe; see https://kaidoplan.cygnusyang.top/#pricing |


## License

This repository (plugin manifest, MCP configuration, hook scripts, slash commands, wrapper scripts) is released under the [MIT License](LICENSE) — fork it, tweak it, ship your own flavor; improvements welcome via PR in this repo.

The KaidoPlan application and CLI binaries it orchestrates remain proprietary and require a valid license or subscription.
