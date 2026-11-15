#!/usr/bin/env python3
"""Check GitFlow PR title and target branch. No GitHub write token needed."""
import os
import re
import sys


def validate(base: str, head: str, title: str) -> None:
    allowed = re.compile(r"^(feat|fix|perf|refactor|docs|test|chore|build|ci)(\([^)]+\))?!?: .+")
    if base == "develop":
        if not re.match(r"^(feature|bugfix|hotfix|release|chore|docs)/", head):
            raise ValueError("PRs into develop must come from feature/*, bugfix/*, hotfix/*, release/*, chore/* or docs/*")
        if not allowed.fullmatch(title):
            raise ValueError("Use a Conventional Commit PR title, such as 'feat: add discount' or 'fix: correct calculation'")
        if head.startswith("feature/") and not title.startswith(("feat:", "feat(" ,"feat!:")):
            raise ValueError("A feature/* branch should use a feat: PR title")
        if head.startswith("bugfix/") and not title.startswith(("fix:", "fix(", "fix!:")):
            raise ValueError("A bugfix/* branch should use a fix: PR title")
        return
    if base == "main":
        if re.fullmatch(r"release/\d+\.\d+\.\d+", head):
            if not title.startswith("release:"):
                raise ValueError("Use 'release: X.Y.Z' for a release PR into main")
            return
        if re.fullmatch(r"hotfix/\d+\.\d+\.\d+", head):
            if not title.startswith("fix:"):
                raise ValueError("Use 'fix: ...' for a hotfix PR into main")
            return
        raise ValueError("Only release/X.Y.Z and hotfix/X.Y.Z can PR into main")
    if base.startswith("release/"):
        if not head.startswith("bugfix/") or not title.startswith("fix:"):
            raise ValueError("Only bugfix/* with a fix: title can PR into release/*")
        return
    raise ValueError(f"Unsupported PR target: {base}")


if __name__ == "__main__":
    try:
        validate(os.environ.get("PR_BASE_REF", ""), os.environ.get("PR_HEAD_REF", ""), os.environ.get("PR_TITLE", ""))
        print("PR title/branch policy: OK")
    except ValueError as error:
        print(f"PR policy failed: {error}", file=sys.stderr)
        sys.exit(1)
