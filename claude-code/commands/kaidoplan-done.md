---
description: Mark a KaidoPlan task done and report the group's progress
argument-hint: <task ID or ID prefix>
---

Mark task `$ARGUMENTS` as done.

Steps:

1. If no project is open in this session yet, open the file `KAIDOPLAN_PROJECT` points at with
   `project_open` (ask the user when it is unset).
2. Call `status_update` with `{"taskID": "<full ID or prefix>", "status": "done"}`. The tool returns the
   task title, `completedAt` and the new status; on failure, report the structured error verbatim.
3. Read the task's `parentID` with `task_get`. If it has a parent, call `status_update` again with only
   `taskID` (no `status` / `progress`) to read `groupProgress`.
4. Report: task title, completion time, status, and the group's progress percentage. With no parent,
   report the task alone.

Constraints:

- When the ID does not exist or the prefix is ambiguous, list the candidates and let the user choose.
  Never guess.
- Do not touch other fields: `done` already sets progress to 100%.

Reply to the user in the language they are writing in.
