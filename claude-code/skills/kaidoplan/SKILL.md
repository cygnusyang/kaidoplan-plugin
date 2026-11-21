---
name: kaidoplan
description: Plan, add, schedule, inspect, or complete tasks in a specific KaidoPlan project. Use when another skill delegates task persistence or asks for WBS, scheduling, status, or progress in a .kaido file.
---

# KaidoPlan

## Handoff from another skill

The caller supplies an operation (`plan`, `status`, or `done`) and the target project's absolute `.kaido` path. For `plan`, supply requirements or a WBS and any known dates or dependencies. For `done`, supply the task ID or a unique prefix. A caller can ask the host to load this skill, or follow this contract and invoke the KaidoPlan MCP tools directly. There is no required host-specific skill-to-skill API.

For interactive use, resolve the target from the user's explicit path, otherwise from the project's documented path or `KAIDOPLAN_PROJECT`. If no unique target can be established, stop before writing and request the path. Resolve relative paths against the caller's project root before invoking tools, and require a `.kaido` destination. Never select the first matching file, reuse a previously opened project by default, or create a replacement when opening fails.

## File and tool rules

- Pass the target path as an argument to KaidoPlan. All project reads, writes, and verification must go through KaidoPlan MCP or the official `kaidoplan` CLI. Never open, inspect, or edit the `.kaido` file through an editor, generic file tool, shell command, or script. Never create a task JSON file. Pass WBS data in memory as MCP arguments.
- **MCP** — Start every operation by invoking KaidoPlan's MCP tool `project_open` with the target path, even if the session already has a project loaded. `project_open` tells the server to load the project. Invoke `project_create` through MCP only when creation at that path was requested. Use the tool's advertised schema. Stop on error or if the target cannot be confirmed. Run project selection, operation, and verification serially in one session, and use separate sessions for concurrent operations on different files.
- **CLI** — Include `--file <absolute-path>` on every project command. For example, run `kaidoplan task list --file "/absolute/path/to/project.kaido"` to query tasks. KaidoPlan handles loading and saving internally. CLI JSON output may be consumed in memory. Use MCP `wbs_import` for structured WBS import. See the [KaidoPlan CLI reference](references/cli.md) for more commands and version checks.
- Serialize writers to the same project. If neither supported interface can perform the requested operation, report the failure and stop.

## Operations

- **Plan** — List tasks first with `task_list`. Reconcile with existing entries and import only new work through `wbs_import`, using the advertised schema. For existing tasks, use the relevant task update tool. Model milestones, groups, and leaf tasks. Estimate leaves in person-hours and keep acceptance criteria with the task where supported. Use confirmed dates and dependencies, then call `schedule_compute`, `schedule_critical_path`, and `violations_list`. Report violations without changing dates or dependencies to hide them.
- **Status** — Use `task_list`, `schedule_critical_path`, and `violations_list` for the selected file. Report available schedule and progress data. Computing a fresh schedule may save changes and requires a planning operation.
- **Done** — Resolve the task to a unique ID in the selected file. Call `status_update` with that ID and status `done`. Verify via `task_get` and report completion. If the ID is ambiguous, return the candidates. A completion retry for an already completed task should report the existing status.

After a write, read the affected tasks back through KaidoPlan. Return the resolved project path, operation, affected task IDs and statuses, and any scheduling violations or tool errors. Report saved steps and remaining work separately if an operation partially fails.
