# KaidoPlan Claude Code Plugin

**English** · [简体中文](README.zh-CN.md)

Plug KaidoPlan's planning capability into Claude Code: slash commands drive WBS breakdown, scheduling, violation review and status write-back, over the MCP tools underneath (same contract as ADR-005).

## Prerequisites

1. Build the MCP server in this repository:

   ```bash
   swift build -c release
   ```

2. Set `KAIDOPLAN_PROJECT` to the `.kaido` file path (put it in your shell config, or supply it at the prompt).

## Loading

```bash
claude --plugin-dir /path/to/KaidoPlan/Plugins/claude-code
```

The MCP launcher locates the server in this order:

1. The executable named by the `KAIDOPLAN_MCP_BIN` environment variable;
2. `.build/release/KaidoPlanMCP` in the repository;
3. `.build/debug/KaidoPlanMCP` in the repository.

Once loaded, the hook looks up `KaidoPlanCLI` in the same order (`KAIDOPLAN_CLI_BIN` → release → debug). When the plugin is installed outside the repository via a marketplace, the latter two paths do not exist and both environment variables must be set.

If none of the three is found, the script writes the reason to stderr and exits non-zero.

## Commands

| Command | Effect |
|---|---|
| `/kaidoplan plan <requirement>` | Read the requirement, build the WBS, schedule, list violations |
| `/kaidoplan done <task-ID>` | Mark the task done and report group completion |
| `/kaidoplan status` | Task table, critical path and violation summary |

Task IDs accept a full UUID or a **unique prefix of at least 4 characters**.

## Registered hooks

`hooks/hooks.json` registers the `TaskCompleted` event, which calls `bin/kaidoplan-task-hook`:

1. Reads `task_subject` (the Claude Code task title) from the event JSON.
2. Reads the project at `KAIDOPLAN_PROJECT` with `KaidoPlanCLI task list --json` and matches by exact title.
3. When exactly one task matches and its status is not `done`, runs `kaidoplan status update <id> --status done`.

The title is the join key between the two task systems — a **convention, not a hard constraint**:

- `/kaidoplan plan` only imports the KaidoPlan WBS; it does not create Claude Code tasks. When you want automatic write-back, create a Claude Code task with the same title for that work item.
- KaidoPlan does not enforce title uniqueness. With duplicate titles the hook skips; when different work items share a title the hook may mark the wrong one, so titles taking part in write-back must be unique within the project.

Safety boundaries:

- On 0 or multiple matches, a missing `KAIDOPLAN_PROJECT`, a missing `KaidoPlanCLI`, or an invalid event format, the hook only writes the reason to stderr — no write-back, and Claude Code's task completion is never blocked. Except for a missing Python interpreter, the hook always exits 0.
- The hook writes the `.kaido` file directly through the CLI; the app does not refresh automatically. Editing on both sides at once overwrites: if the hook writes first and the app saves later, the app's stale in-memory data overwrites the write-back. Close the app during write-back, or reopen it before editing.
- `KAIDOPLAN_CLI_BIN` sets the CLI path; `KAIDOPLAN_MCP_BIN` sets the MCP server path — the two are independent.
- The hook takes an exclusive lock keyed by the project's real path (lock file in the system temp dir), so parallel subagents completing multiple tasks at once do not overwrite each other's write-back.
- `task list --json` outputs a bare array (easy to iterate in scripts); MCP `task_list` returns `{"tasks": [...]}`. Both interfaces carry identical fields — only the envelope differs.
