#!/usr/bin/env python3
"""Release tag calculator for GitFlow. Python standard library only.

Workflow assumptions:
  - Feature PRs are squash-merged into develop, with a Conventional Commit title.
  - Release PRs are MERGE-committed into main (not squash/rebase).
  - Tags are immutable; the CI workflow serializes version/tag creation.
  - On push, the current checkout is the exact commit being published.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

STABLE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
DEV = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-dev\.(\d+)$")
RC = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-rc\.(\d+)$")
RELEASE_BRANCH = re.compile(r"^(release|hotfix)/(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def run(*args: str) -> str:
    return subprocess.check_output(["git", *args], encoding="utf-8").strip()


def tags() -> list[str]:
    output = run("tag", "--list", "v*")
    return output.splitlines() if output else []


def stable_versions(all_tags: list[str]) -> list[Version]:
    return sorted((Version(*map(int, m.groups())) for t in all_tags if (m := STABLE.fullmatch(t))))


def change_type(message: str) -> str:
    """Classify a squash commit or a GitHub merge commit.

    GitHub's default merge message is e.g.:
      Merge pull request #15 from owner/feature/foo

      feat: add inventory
    The PR title in the body is what must be classified.
    """
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    candidates = lines[1:] if lines and lines[0].startswith("Merge pull request #") else lines[:1]
    if re.search(r"(?mi)^BREAKING[ -]CHANGE\s*:", message):
        return "breaking"
    for line in candidates:
        if re.match(r"^[a-z][\w-]*(\([^)]+\))?!:", line):
            return "breaking"
        if re.match(r"^feat(\([^)]+\))?:", line):
            return "feat"
        if re.match(r"^(fix|perf)(\([^)]+\))?:", line):
            return "fix"
    return "none"


def bump(base: Version, kind: str) -> Version:
    if kind == "breaking":
        return Version(base.major + 1, 0, 0)
    if kind == "feat":
        return Version(base.major, base.minor + 1, 0)
    if kind == "fix":
        return Version(base.major, base.minor, base.patch + 1)
    return base  # docs/chore/test/ci do NOT increment PATCH


def next_dev(stable: Version, previous: tuple[Version, int] | None, kind: str) -> tuple[Version, int]:
    """Pick next pre-release build, preserving a higher, unpublished target."""
    candidate = bump(stable, kind)
    if previous is None or previous[0] <= stable:
        return (candidate, 1)
    base, index = previous
    new_base = max(base, candidate)
    return (new_base, index + 1 if new_base == base else 1)


def unpublished_change_type(sha: str, stable_tag: str | None) -> str:
    """Find strongest semantic change on develop since the last stable baseline.

    Only first-parent commits are inspected to avoid double-counting the
    individual commits in GitHub merge commits. If a stable release commit is
    not directly on develop, use their merge base as the range boundary.
    """
    start = None
    if stable_tag:
        stable_commit = run("rev-parse", f"{stable_tag}^{{commit}}")
        start = run("merge-base", stable_commit, sha)
    revision_range = f"{start}..{sha}" if start else sha
    commits = run("rev-list", "--first-parent", "--reverse", revision_range).splitlines()
    ranking = {"none": 0, "fix": 1, "feat": 2, "breaking": 3}
    strongest = "none"
    for commit in commits:
        # Before the initial release, ignore commit messages in the original
        # repository bootstrap unless they are semantic changes.
        message = run("show", "-s", "--format=%B", commit)
        current = change_type(message)
        if ranking[current] > ranking[strongest]:
            strongest = current
    return strongest


def previous_dev_tag(all_tags: list[str], sha: str) -> tuple[Version, int] | None:
    """Pick nearest dev tag along develop's FIRST-PARENT commit ancestry."""
    by_commit: dict[str, list[tuple[Version, int]]] = {}
    for t in all_tags:
        match = DEV.fullmatch(t)
        if not match:
            continue
        commit = run("rev-parse", f"{t}^{{commit}}")
        numbers = tuple(map(int, match.groups()))
        by_commit.setdefault(commit, []).append((Version(*numbers[:3]), numbers[3]))
    for commit in run("rev-list", "--first-parent", sha).splitlines():
        if commit in by_commit:
            return max(by_commit[commit])
    return None


def same_commit_tag(all_tags: list[str], pattern: re.Pattern[str], sha: str) -> str | None:
    for tag in all_tags:
        if pattern.fullmatch(tag) and run("rev-parse", f"{tag}^{{commit}}") == sha:
            return tag
    return None


def calculate(kind: str, branch: str, sha: str) -> tuple[str, bool]:
    all_tags = tags()
    latest_stable = max(stable_versions(all_tags), default=Version(0, 0, 0))
    if kind == "dev":
        existing = same_commit_tag(all_tags, DEV, sha)
        if existing:
            return existing, False
        prior = previous_dev_tag(all_tags, sha)
        stable_tags = [t for t in all_tags if STABLE.fullmatch(t)]
        latest_tag = max(stable_tags, key=lambda t: Version(*map(int, STABLE.fullmatch(t).groups()))) if stable_tags else None
        semantic_kind = unpublished_change_type(sha, latest_tag)
        version, number = next_dev(latest_stable, prior, semantic_kind)
        return f"v{version}-dev.{number}", True

    match = RELEASE_BRANCH.fullmatch(branch)
    if not match:
        raise ValueError(f"Only release/X.Y.Z and hotfix/X.Y.Z allowed, got: {branch}")
    version = Version(*map(int, match.groups()[1:]))
    if version <= latest_stable and f"v{version}" not in all_tags:
        raise ValueError(f"Release {version} must be newer than latest stable {latest_stable}")

    if kind == "rc":
        existing = same_commit_tag(all_tags, RC, sha)
        if existing:
            # A commit can have only one RC tag per release in this lab.
            if not existing.startswith(f"v{version}-rc."):
                raise ValueError(f"Commit already carries a different RC: {existing}")
            return existing, False
        if version <= latest_stable:
            raise ValueError(f"Cannot create a new RC for {version}: stable {latest_stable} is already published")
        numbers = [int(m.group(4)) for t in all_tags
                   if (m := RC.fullmatch(t)) and Version(*map(int, m.groups()[:3])) == version]
        return f"v{version}-rc.{max(numbers, default=0) + 1}", True

    if kind == "stable":
        tag = f"v{version}"
        if tag in all_tags:
            if run("rev-parse", f"{tag}^{{commit}}") != sha:
                raise ValueError(f"Tag {tag} already points to another commit")
            return tag, False
        if version <= latest_stable:
            raise ValueError(f"Version {version} must exceed latest stable {latest_stable}")
        if match.group(1) == "release":
            release_rcs = [t for t in all_tags if (m := RC.fullmatch(t))
                           and Version(*map(int, m.groups()[:3])) == version]
            if not release_rcs:
                raise ValueError(f"Missing staging RC tag for release {version}")
            newest = max(release_rcs, key=lambda t: int(RC.fullmatch(t).group(4)))
            rc_commit = run("rev-parse", f"{newest}^{{commit}}")
            # Requires a proper merge commit from release into main.
            if subprocess.run(["git", "merge-base", "--is-ancestor", rc_commit, sha], check=False).returncode != 0:
                raise ValueError("Approved RC commit is not an ancestor of final main commit. Use a merge commit, not squash, for releases.")
        return tag, True
    raise ValueError(f"Unexpected --kind {kind}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["dev", "rc", "stable"], required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--sha", required=True)
    args = p.parse_args()
    sha = run("rev-parse", f"{args.sha}^{{commit}}")
    if run("rev-parse", "HEAD") != sha:
        raise ValueError("Checkout must be at the exact commit being published")
    tag, is_new = calculate(args.kind, args.branch, sha)
    tag_match = re.match(r"^v(\d+\.\d+\.\d+(?:-(?:dev|rc)\.\d+)?)$", tag)
    if not tag_match:
        raise ValueError("Invalid computed version")
    outputs = {
        "tag": tag,
        "version": tag[1:],
        "new": str(is_new).lower(),
        "sha": sha,
        "short_sha": sha[:12],
    }
    for key, value in outputs.items():
        print(f"{key}={value}")
    if output := os.getenv("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
