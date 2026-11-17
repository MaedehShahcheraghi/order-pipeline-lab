#!/usr/bin/env python3
"""GitFlow PR gate: a PR title is a traceable semantic change classification."""
import os
import re
import sys

CC = re.compile(r"^(feat|fix|perf|refactor|docs|test|chore|build|ci|sync)(\([^)]+\))?!?: .+$")
BR = re.compile(r"^(release|hotfix)/\d+\.\d+\.\d+$")


def verb(title):
    match = CC.fullmatch(title)
    return match.group(1) if match else None


def validate(base: str, head: str, title: str) -> None:
    kind = verb(title)
    if base == "develop":
        if not re.match(r"^(feature|bugfix|chore|docs|ci|sync|release|hotfix)/", head):
            raise ValueError("develop accepts feature/*, bugfix/*, chore/*, docs/*, ci/*, sync/*, release/*, hotfix/*")
        if not kind:
            raise ValueError("Use Conventional Commit PR title, e.g. feat: add stock")
        if head.startswith("feature/") and kind != "feat":
            raise ValueError("feature/* needs feat: title")
        if head.startswith("bugfix/") and kind not in ("fix", "perf"):
            raise ValueError("bugfix/* needs fix: or perf: title")
        if head.startswith(("sync/", "release/", "hotfix/")) and kind != "sync":
            raise ValueError("forward-port to develop must use sync: title (not fix:)")
        if head.startswith("chore/") and kind != "chore":
            raise ValueError("chore/* needs chore: title")
        return
    if base == "main":
        m = BR.fullmatch(head)
        if not m:
            raise ValueError("main only accepts release/X.Y.Z or hotfix/X.Y.Z")
        if head.startswith("release/") and title != f"release: {head[len('release/'):]}" :
            raise ValueError("Release MR title must match branch exactly: release: X.Y.Z")
        if head.startswith("hotfix/") and kind != "fix":
            raise ValueError("Hotfix MR needs fix: title")
        return
    if base.startswith(("release/", "hotfix/")):
        if head.startswith("bugfix/") and kind in ("fix", "perf"):
            return
        if base.startswith("release/") and head.startswith("sync/") and kind == "sync":
            return  # Explicitly reviewed production hotfix forward-port to QA.
        raise ValueError("QA branch accepts bugfix/* with fix:/perf:; release also accepts sync/* with sync:")
    raise ValueError(f"Unsupported target branch: {base}")


if __name__ == "__main__":
    try:
        validate(os.getenv("PR_BASE_REF", ""), os.getenv("PR_HEAD_REF", ""), os.getenv("PR_TITLE", ""))
        print("PR policy: OK")
    except ValueError as e:
        print(f"PR policy failed: {e}", file=sys.stderr)
        sys.exit(1)
