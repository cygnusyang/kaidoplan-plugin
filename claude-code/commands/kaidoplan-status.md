---
description: Summarise the plan, critical path and violations of a KaidoPlan project
---

Summarise the current KaidoPlan project.

Steps:

1. If no project is open in this session yet, open the file `KAIDOPLAN_PROJECT` points at with
   `project_open` (ask the user when it is unset).
2. Call, in order:
   - `task_list` (no arguments) for the task list;
   - `schedule_compute` for the schedule;
   - `schedule_critical_path` for the critical path and slack;
   - `violations_list` for violations.
3. Print one compact table row per task: ID prefix, title, status, progress, duration in days, planned
   start/end, total slack. Indent group rows by depth; milestones have zero duration.
4. List every violation with its code, the tasks involved and the reason.
5. Close with three summary lines: task count (done / in progress / pending / blocked), critical-path task
   count, violation count.

Constraints:

- Read-only: do not modify any task.
- When the schedule or violation tools return an error, relay the code and message verbatim; never
  substitute an estimate.

Reply to the user in the language they are writing in.
