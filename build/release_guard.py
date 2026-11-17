#!/usr/bin/env python3
"""Fail early if a release cannot be promoted unchanged to Stable.

pre-cut: verify the shared publication workflow on develop matches main.
pre-merge: verify the GitHub-generated test merge tree equals the latest
            successfully tagged release/hotfix RC, before anyone merges to main.

The stricter stable check in build/versioning.py remains authoritative.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

WORKFLOW = '.github/workflows/build-release.yml'
RELEASE_REF = re.compile(r'^(release|hotfix)/(\d+)\.(\d+)\.(\d+)$')
RC_TAG = re.compile(r'^v(\d+)\.(\d+)\.(\d+)-rc\.([1-9]\d*)$')


class GuardError(Exception):
    pass


def git(*args: str, ok: bool = True) -> str:
    completed = subprocess.run(['git', *args], text=True, capture_output=True)
    if ok and completed.returncode:
        raise GuardError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def cut_guard() -> None:
    """Used when Prepare Release checked out the exact develop HEAD."""
    main_blob = git('rev-parse', f'origin/main:{WORKFLOW}')
    dev_blob = git('rev-parse', f'HEAD:{WORKFLOW}')
    if main_blob != dev_blob:
        raise GuardError(
            'Release Cut blocked: build-release.yml differs between main and develop.\n'
            'Sync the publisher workflow FROM main INTO develop via a reviewed ci/* PR,\n'
            'wait for its Dev pipeline to publish and tag the new develop HEAD,\n'
            'then rerun Prepare Release. Do NOT create release/cut refs manually.\n'
            'Difference:\n' + git('diff', 'origin/main', 'HEAD', '--', WORKFLOW)
        )
    print('Release Cut CI preflight OK: publisher workflow matches main')


def premerge_guard(head_ref: str, expected_head: str = '') -> None:
    """Actions/checkout on pull_request must check out refs/pull/N/merge.

    HEAD must be GitHub's synthetic test merge commit with two parents.  Its
    tree is what the actual PR merge should produce unless main changes.
    """
    match = RELEASE_REF.fullmatch(head_ref)
    if not match:
        raise GuardError('Stable PR must come from release/X.Y.Z or hotfix/X.Y.Z')
    version = '.'.join(match.groups()[1:])
    parents = git('rev-list', '--parents', '-n', '1', 'HEAD').split()
    if len(parents) != 3:
        raise GuardError(
            'Expected synthetic GitHub PR test merge (HEAD with two parents); '
            'checkout pull_request merge ref with fetch-depth: 0'
        )
    merged_sha, main_parent, head_parent = parents
    if expected_head and head_parent != expected_head:
        raise GuardError('Synthetic merge source SHA does not match current PR head')
    rc_tags: list[tuple[int, str]] = []
    for name in git('tag', '--list', f'v{version}-rc.*').splitlines():
        m = RC_TAG.fullmatch(name)
        if m and '.'.join(m.groups()[:3]) == version:
            rc_tags.append((int(m.group(4)), name))
    if not rc_tags:
        raise GuardError(f'No published RC tags for {version}. Publish/test RC before merging.')
    rc_name = max(rc_tags)[1]
    rc_sha = git('rev-parse', f'{rc_name}^{{commit}}')
    if rc_sha != head_parent:
        raise GuardError(
            f'{rc_name} is NOT at the release branch HEAD used in this PR.\n'
            'Finish RC build/publish and rerun PR checks before merging.'
        )
    rc_tree = git('rev-parse', f'{rc_name}^{{tree}}')
    merge_tree = git('rev-parse', 'HEAD^{tree}')
    if rc_tree != merge_tree:
        changes = git('diff', '--name-status', rc_name, 'HEAD')
        raise GuardError(
            f'PR would publish an UNTESTED tree: synthetic main merge differs from {rc_name}.\n'
            'Bring needed main changes into the release branch, produce a NEW RC,\n'
            'then rerun the PR checks. Do not squash or ignore this failure.\n'
            f'Different paths:\n{changes}'
        )
    print(f'PRE-MERGE OK: latest {rc_name} and proposed main merge have identical trees')
    print(f'RC commit: {rc_sha}; test merge commit: {merged_sha}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pre-cut', 'pre-merge'])
    parser.add_argument('--head-ref', default='')
    parser.add_argument('--head-sha', default='')
    args = parser.parse_args()
    try:
        if args.mode == 'pre-cut':
            cut_guard()
        else:
            premerge_guard(args.head_ref, args.head_sha)
    except GuardError as exc:
        print(f'RELEASE GUARD FAILED: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
