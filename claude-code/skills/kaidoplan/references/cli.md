# KaidoPlan CLI reference

Use the official `kaidoplan` executable. Pass `--file "<absolute .kaido path>"` on every project command. KaidoPlan handles project loading and saving. Keep structured WBS input in MCP tool arguments and use `wbs_import` through MCP.

## Check the installed CLI

Run `kaidoplan --help` to list its commands and use subcommand help to confirm flags before relying on a command. For example:

```sh
kaidoplan task --help
kaidoplan status update --help
```

The table lists commands documented by the KaidoPlan plugin repository. The Homebrew formula pins macOS CLI release 4.0.0 and includes a smoke test for `project create --file`. Use the installed binary's help for version-specific syntax and additional commands. [Official Homebrew formula](https://github.com/cygnusyang/homebrew-kaidoplan/blob/main/Formula/kaidoplan-cli.rb) · [Plugin walkthrough at 602c8ec](https://github.com/cygnusyang/kaidoplan-plugin/blob/602c8ec/README.md)

## Project commands

In these examples, `"$project"` is the caller-supplied absolute path and `"$task_id"` is an ID resolved from that project.

| Operation | Command |
|---|---|
| Create a project when requested | `kaidoplan project create "Demo Project" --start 2026-11-02 --end 2026-11-20 --file "$project"` |
| List tasks | `kaidoplan task list --file "$project"` |
| List tasks for in-memory processing | `kaidoplan task list --json --file "$project"` |
| Set a task dependency | `kaidoplan task update "$task_id" --dep "${predecessor_id}:fs" --file "$project"` |
| Compute and save the schedule | `kaidoplan schedule compute --file "$project"` |
| Read the critical path | `kaidoplan schedule path --file "$project"` |
| List schedule violations | `kaidoplan violations --file "$project"` |
| Complete a task | `kaidoplan status update "$task_id" --status done --file "$project"` |

Use `task list` against the same project to verify task updates. If the installed CLI lacks the requested operation, use the corresponding KaidoPlan MCP tool when available. Keep any JSON returned by the CLI in memory.
