#!/usr/bin/env python3
"""Claude Code TaskCompleted hook: write the matching KaidoPlan task status back.

Input: the event JSON Claude Code writes to stdin (hook_event_name ==
"TaskCompleted", carrying task_subject). KaidoPlan tasks have no shared ID space
with Claude Code tasks, so the title is the only stable key between the two.

Rules:
- Write back only when KAIDOPLAN_PROJECT points at a .kaido file and the title
  matches exactly one KaidoPlan task.
- Tasks already marked done are skipped; zero or several matches only print to
  stderr and leave the data untouched.
- Always exit 0: a hook must never block task completion in the host.
- Take an exclusive lock on the project so parallel sub-agents finishing at the
  same time cannot overwrite each other's write-back.
"""

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata


def find_cli():
    """Same order as bin/kaidoplan-mcp: env var, build products, PATH, none."""
    override = os.environ.get("KAIDOPLAN_CLI_BIN")
    if override:
        return override
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    for configuration in ("release", "debug"):
        candidate = os.path.join(root, ".build", configuration, "KaidoPlanCLI")
        if os.access(candidate, os.X_OK):
            return candidate
    # The standalone plugin repo has no .build directory: use the PATH binary.
    # Kept after the build products so local builds in the main repo still win.
    return shutil.which("kaidoplan")


def note(message):
    """Write one line to stderr, stripping control characters."""
    clean = "".join(ch for ch in str(message) if unicodedata.category(ch)[0] != "C")
    print(f"kaidoplan-hook: {clean}", file=sys.stderr)


def normalize(text):
    """Normalise Unicode form and surrounding whitespace before comparing titles."""
    return unicodedata.normalize("NFC", text).strip()


def run(cli, args):
    """Run the CLI and return (ok, stdout, stderr)."""
    try:
        result = subprocess.run(
            [cli] + args, capture_output=True, text=True, encoding="utf-8", timeout=10
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, "", str(error)
    return result.returncode == 0, result.stdout, result.stderr


def sync_status(cli, project, subject):
    """Read the task list, match the title and write the status back, all under lock."""
    ok, stdout, stderr = run(cli, ["task", "list", "--json", "--file", project])
    if not ok:
        note(f"could not read the task list: {stderr.strip()}")
        return

    try:
        tasks = json.loads(stdout)
    except json.JSONDecodeError:
        note("task list is not valid JSON, skipping")
        return
    if not isinstance(tasks, list):
        note("task list has an unexpected shape, skipping")
        return

    matches = [
        task
        for task in tasks
        if isinstance(task, dict)
        and isinstance(task.get("title"), str)
        and normalize(task["title"]) == subject
    ]
    if len(matches) != 1:
        note(f'"{subject}" matches {len(matches)} KaidoPlan tasks, skipping write-back')
        return

    task = matches[0]
    if task.get("status") == "done":
        return

    ok, _, stderr = run(
        cli,
        ["status", "update", str(task.get("id", "")), "--status", "done", "--file", project],
    )
    if ok:
        note(f'wrote back "{subject}" as done')
    else:
        note(f"status write-back failed: {stderr.strip()}")


def main():
    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        note("input is not valid JSON, skipping")
        return 0
    if not isinstance(event, dict):
        note("event is not a JSON object, skipping")
        return 0

    if event.get("hook_event_name") != "TaskCompleted":
        return 0

    raw_subject = event.get("task_subject")
    if not isinstance(raw_subject, str):
        return 0
    subject = normalize(raw_subject)
    project = os.environ.get("KAIDOPLAN_PROJECT")
    if not subject or not project:
        return 0

    if not os.path.isabs(project):
        cwd = event.get("cwd")
        if not isinstance(cwd, str) or not os.path.isabs(cwd):
            note("a relative KAIDOPLAN_PROJECT requires the event working directory")
            return 0
        project = os.path.join(cwd, project)
    project = os.path.realpath(project)
    if not project.lower().endswith(".kaido") or not os.path.isfile(project):
        note("KAIDOPLAN_PROJECT must identify an existing .kaido file")
        return 0

    cli = find_cli()
    if cli is None:
        note("KaidoPlanCLI not found, skipping (run swift build, install via Homebrew, or set KAIDOPLAN_CLI_BIN)")
        return 0

    # The CLI writes atomically, so the project file's inode changes and locking it
    # directly is useless. Lock a stable path derived from the real project path.
    lock_name = "kaidoplan-hook-" + hashlib.sha256(project.encode()).hexdigest()[:16] + ".lock"
    lock_path = os.path.join(tempfile.gettempdir(), lock_name)
    try:
        with open(lock_path, "a") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                sync_status(cli, project, subject)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError as error:
        note(f"could not take the project lock: {error}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - a hook must not block task completion
        note(f"unexpected error, skipping: {error}")
        sys.exit(0)
