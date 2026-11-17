"""Integration tests for pre-cut and PR synthetic merge protections."""
import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'release_guard.py'
if not SOURCE.exists():  # tests inside standalone repair archive
    SOURCE = Path(__file__).resolve().parents[1] / 'build' / 'release_guard.py'
spec = importlib.util.spec_from_file_location('release_guard', SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def git(cwd, *args):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, stderr=subprocess.PIPE).strip()


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        git(self.d, 'init', '-q', '-b', 'main')
        git(self.d, 'config', 'user.email', 'test@example.com')
        git(self.d, 'config', 'user.name', 'Test')
        self.put('.github/workflows/build-release.yml', 'pipeline: v1\n')
        git(self.d, 'add', '.')
        git(self.d, 'commit', '-qm', 'initial')
        git(self.d, 'branch', 'origin/main')
        git(self.d, 'switch', '-c', 'develop')

    def put(self, name, content):
        f = Path(self.d) / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)

    def commit(self, name, content, msg):
        self.put(name, content)
        git(self.d, 'add', name)
        git(self.d, 'commit', '-qm', msg)

    def guard(self, fn, *args):
        wd = os.getcwd()
        try:
            os.chdir(self.d)
            return fn(*args)
        finally:
            os.chdir(wd)

    def test_cut_accepts_matching_publisher_file(self):
        self.commit('feature.txt', 'a\n', 'feat: test')
        self.guard(guard.cut_guard)

    def test_cut_rejects_mismatch(self):
        self.commit('.github/workflows/build-release.yml', 'pipeline: v2\n', 'ci: changed pipeline')
        with self.assertRaisesRegex(guard.GuardError, 'differs between main and develop'):
            self.guard(guard.cut_guard)

    def setup_release(self):
        self.commit('feature.txt', 'v1\n', 'feat: new feature')
        git(self.d, 'switch', '-c', 'release/0.2.0')
        git(self.d, 'tag', '-a', 'v0.2.0-rc.1', '-m', 'RC1')
        return git(self.d, 'rev-parse', 'HEAD')

    def test_synthetic_merge_exact_rc_passes(self):
        rc_head = self.setup_release()
        git(self.d, 'switch', '-c', 'pr-test-merge', 'main')
        git(self.d, 'merge', '--no-ff', '-m', 'PR test merge', 'release/0.2.0')
        self.guard(guard.premerge_guard, 'release/0.2.0', rc_head)

    def test_synthetic_merge_with_extra_main_change_fails(self):
        rc_head = self.setup_release()
        git(self.d, 'switch', 'main')
        self.commit('main_only.txt', 'old main drift\n', 'ci: changed on main')
        git(self.d, 'switch', '-c', 'pr-test-merge')
        git(self.d, 'merge', '--no-ff', '-m', 'PR test merge', 'release/0.2.0')
        with self.assertRaisesRegex(guard.GuardError, 'UNTESTED tree'):
            self.guard(guard.premerge_guard, 'release/0.2.0', rc_head)

    def test_synthetic_merge_rejects_stale_rc(self):
        self.setup_release()
        self.commit('feature.txt', 'v2\n', 'fix: qa bug')
        new_head = git(self.d, 'rev-parse', 'HEAD')
        git(self.d, 'switch', '-c', 'pr-test-merge', 'main')
        git(self.d, 'merge', '--no-ff', '-m', 'PR test merge', 'release/0.2.0')
        with self.assertRaisesRegex(guard.GuardError, 'NOT at the release branch HEAD'):
            self.guard(guard.premerge_guard, 'release/0.2.0', new_head)


if __name__ == '__main__':
    unittest.main()
