---
description: Read a requirement and build the WBS, schedule and violations in KaidoPlan
argument-hint: <path to a requirements document, or a requirement description>
---

Run one "requirement → WBS → schedule" planning pass in KaidoPlan.

Requirement input: $ARGUMENTS

Steps:

1. **Pick the project file**: prefer the `.kaido` path in `KAIDOPLAN_PROJECT`; ask the user when it is unset.
   If the file exists call `project_open`; otherwise call `project_create` with `path` pointing at that
   location (creating a project writes it to disk; every successful write tool call saves afterwards, so
   an explicit `project_save` is not needed).
2. **Read the requirement**: when the input is a file path, read that file in full; otherwise use the text
   as given. Extract deliverables, milestones, ordering constraints and unknowns.
3. **Break down the WBS**: shape the result as nested JSON (`title`, `kind`, `effortHours`, `children`) and
   import it in one call with `wbs_import`. Estimate leaf effort in hours at 8 hours per person-day;
   confirm anything uncertain with the user before importing.
4. **Schedule**: call `schedule_compute`. Take the project start/end from the user or the project metadata;
   if neither exists, ask first — never invent dates.
5. **Violations**: call `violations_list`. Explain each one in a single sentence: type, tasks involved, why.
   Do not silently change deadlines or dependencies; propose the fix to the user first.
6. **Summarise**: task count, project start/end, critical path (`schedule_critical_path`) and violation count.

Constraints:

- This command only builds the plan; it does not write implementation code.
- Use the terminology from the requirement for task titles, and use one name per thing throughout.
- Every leaf must carry an effort estimate; groups and milestones carry none.

Reply to the user in the language they are writing in.
