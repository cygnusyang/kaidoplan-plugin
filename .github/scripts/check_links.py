#!/usr/bin/env python3
"""Check that relative markdown links in the repo point at existing files.

The published READMEs must not carry dead relative links: the source of truth
links into docs/ trees the standalone repo does not contain, and the sync step
rewrites or strips those. This script is the guardrail.

Usage: python3 check_links.py [root-dir]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    bad: list[str] = []
    for md in sorted(root.rglob("*.md")):
        if ".github" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#")[0]
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                bad.append(f"{md.relative_to(root)} -> {target}")
    if bad:
        print("dead relative links:", file=sys.stderr)
        for item in bad:
            print("  " + item, file=sys.stderr)
        return 1
    print("ok: no dead relative links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
