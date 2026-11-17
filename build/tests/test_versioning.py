"""Unit tests (pure) + short integration tests with actual isolated Git repositories."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "versioning.py"
spec = importlib.util.spec_from_file_location("versioning", MODULE)
v = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = v
spec.loader.exec_module(v)


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.PIPE).strip()


class GitSandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = self.temp.name
        git("init", "-q", "-b", "main", cwd=self.path)
        git("config", "user.name", "Test", cwd=self.path)
        git("config", "user.email", "test@example.com", cwd=self.path)
        self.i = 0
        self.commit("Initial commit")
        self.tag("v0.1.0")
        git("switch", "-c", "develop", cwd=self.path)

    def commit(self, subject):
        self.i += 1
        with open(os.path.join(self.path, f"change{self.i}.txt"), "w", encoding="utf-8") as f:
            f.write(subject)
        git("add", ".", cwd=self.path)
        git("commit", "-qm", subject, cwd=self.path)
        return self.sha()

    def sha(self):
        return git("rev-parse", "HEAD", cwd=self.path)

    def tag(self, t):
        git("tag", "-a", t, "-m", t, cwd=self.path)

    def calc(self, kind, branch):
        with patch.dict(os.environ, {}, clear=False):
            here = os.getcwd()
            try:
                os.chdir(self.path)
                return v.calculate(kind, branch, self.sha())
            finally:
                os.chdir(here)

    def prepare(self, mode):
        here = os.getcwd()
        try:
            os.chdir(self.path)
            return v.prepare(mode, self.sha())
        finally:
            os.chdir(here)

    def cut(self, version):
        self.tag(f"v{version}-dev.1")
        self.tag(f"cut/v{version}")
        git("branch", f"release/{version}", cwd=self.path)

    def test_feat_merge_chore_and_new_cycle(self):
        self.commit("feat: inventory")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.2.0-dev.1")
        self.cut("0.2.0")
        self.commit("feat: discounts")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.3.0-dev.1")
        self.tag("v0.3.0-dev.1")
        self.commit("chore: readme")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.3.0-dev.2")

    def test_fix_after_cut_and_qa_sync(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        self.commit("fix: independent discount bug")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.2.1-dev.1")
        self.tag("v0.2.1-dev.1")
        self.commit("sync(release): QA inventory fix already released")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.2.1-dev.2")

    def test_sync_only_after_cut_is_sha_only(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        self.commit("sync(release): QA fix")
        self.assertEqual(self.calc("dev", "develop").tag, "")
        self.assertTrue(self.calc("dev", "develop").version.startswith("sha-"))

    def test_multiple_fixes_same_cycle(self):
        self.commit("fix: first")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.1.1-dev.1")
        self.tag("v0.1.1-dev.1")
        self.commit("fix: second")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.1.1-dev.2")

    def test_chore_only_is_sha_artifact(self):
        self.commit("chore: docs")
        self.assertEqual(self.calc("dev", "develop").tag, "")

    def test_release_rc_and_stable_promote(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        git("switch", "release/0.2.0", cwd=self.path)
        self.assertEqual(self.calc("rc", "release/0.2.0").tag, "v0.2.0-rc.1")
        self.tag("v0.2.0-rc.1")
        self.commit("fix: qa bug")
        self.assertEqual(self.calc("rc", "release/0.2.0").tag, "v0.2.0-rc.2")
        self.tag("v0.2.0-rc.2")
        git("switch", "main", cwd=self.path)
        git("merge", "--no-ff", "release/0.2.0", "-m", "Merge release/0.2.0", cwd=self.path)
        r = self.calc("stable", "release/0.2.0")
        self.assertEqual((r.tag, r.source_rc), ("v0.2.0", "v0.2.0-rc.2"))
        self.tag("v0.2.0")
        self.assertFalse(self.calc("stable", "release/0.2.0").is_new)

    def test_stable_rejects_untested_merge_changes(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        git("switch", "release/0.2.0", cwd=self.path)
        self.tag("v0.2.0-rc.1")
        git("switch", "main", cwd=self.path)
        self.commit("chore: main changes not in rc")
        git("merge", "--no-ff", "release/0.2.0", "-m", "Merge release/0.2.0", cwd=self.path)
        with self.assertRaisesRegex(ValueError, "differs"):
            self.calc("stable", "release/0.2.0")

    def test_stable_rejects_squash(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        git("switch", "release/0.2.0", cwd=self.path)
        self.tag("v0.2.0-rc.1")
        git("switch", "main", cwd=self.path)
        git("merge", "--squash", "release/0.2.0", cwd=self.path)
        git("commit", "-qm", "release: 0.2.0", cwd=self.path)
        with self.assertRaisesRegex(ValueError, "ancestor"):
            self.calc("stable", "release/0.2.0")

    def test_prepared_hotfix_waits_for_real_fix(self):
        git("switch", "-c", "hotfix/0.1.1", "v0.1.0", cwd=self.path)
        r = self.calc("rc", "hotfix/0.1.1")
        self.assertEqual(r.tag, "")
        self.assertEqual(r.reason, "awaiting hotfix commit")
        self.commit("fix: urgent production issue")
        self.assertEqual(self.calc("rc", "hotfix/0.1.1").tag, "v0.1.1-rc.1")

    def test_release_rc_requires_cut(self):
        self.commit("feat: inventory")
        git("branch", "release/0.2.0", cwd=self.path)
        git("switch", "release/0.2.0", cwd=self.path)
        with self.assertRaisesRegex(ValueError, "cut/v0.2.0"):
            self.calc("rc", "release/0.2.0")

    def test_hotfix_consumes_develop_patch(self):
        self.commit("feat: inventory")
        self.cut("0.2.0")
        git("switch", "release/0.2.0", cwd=self.path)
        self.tag("v0.2.0-rc.1")
        git("switch", "main", cwd=self.path)
        git("merge", "--no-ff", "release/0.2.0", "-m", "Merge release/0.2.0", cwd=self.path)
        self.tag("v0.2.0")
        git("switch", "develop", cwd=self.path)
        self.commit("fix: independent bug a")
        self.tag("v0.2.1-dev.1")
        self.commit("fix: independent bug b")
        self.tag("v0.2.1-dev.2")
        # Production hotfix is prepared from the latest stable tag.
        branch, cut, prod_sha = self.prepare("hotfix")
        self.assertEqual(branch, "hotfix/0.2.1")
        self.assertEqual(prod_sha, git("rev-parse", "v0.2.0^{}", cwd=self.path))
        git("switch", "-c", branch, prod_sha, cwd=self.path)
        self.commit("fix: urgent prod bug")
        self.tag("v0.2.1-rc.1")
        git("switch", "main", cwd=self.path)
        git("merge", "--no-ff", branch, "-m", "Merge hotfix/0.2.1", cwd=self.path)
        self.assertEqual(self.calc("stable", branch).tag, "v0.2.1")
        self.tag("v0.2.1")
        git("switch", "develop", cwd=self.path)
        self.commit("sync(hotfix): production fix forward-port")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.2.2-dev.1")

    def test_prep_release_requires_tagged_head(self):
        self.commit("feat: inventory")
        with self.assertRaisesRegex(ValueError, "tagged develop commit"):
            self.prepare("release")
        self.tag("v0.2.0-dev.1")
        self.assertEqual(self.prepare("release")[:2], ("release/0.2.0", "cut/v0.2.0"))
        self.tag("cut/v0.2.0")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare("release")

    def test_same_sha_stays_immutable(self):
        self.commit("feat: inventory")
        self.tag("v0.2.0-dev.1")
        self.assertEqual(self.calc("dev", "develop").tag, "v0.2.0-dev.1")
        self.assertFalse(self.calc("dev", "develop").is_new)


class PureTests(unittest.TestCase):
    def test_change_type(self):
        self.assertEqual(v.change_type("Merge pull request #7 from x/feature/stuff\n\nfeat: inventory"), "feat")
        self.assertEqual(v.change_type("Merge branch 'feature/demo' into 'develop'\n\nfeat: inventory"), "feat")
        self.assertEqual(v.change_type("sync(release): QA fix from release/0.2.0"), "none")
        self.assertEqual(v.change_type("fix(scope)!: breaks API"), "breaking")
        self.assertEqual(v.change_type("feat: feature\n\nBREAKING CHANGE: breaks JSON schema"), "breaking")
        self.assertEqual(v.change_type("perf(api): improve response"), "fix")
        self.assertEqual(v.change_type("chore: docs"), "none")

    def test_bump(self):
        x = v.Version(0, 2, 3)
        self.assertEqual(str(v.bump(x, "feat")), "0.3.0")
        self.assertEqual(str(v.bump(x, "fix")), "0.2.4")
        self.assertEqual(str(v.bump(x, "breaking")), "1.0.0")
        self.assertEqual(v.bump(x, "none"), x)


if __name__ == "__main__":
    unittest.main()

class PolicyTests(unittest.TestCase):
    def test_pr_rules(self):
        spec = importlib.util.spec_from_file_location('validate_pr', MODULE.parent / 'validate_pr.py')
        policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(policy)
        good = [
            ('develop', 'feature/stock', 'feat: add stock'),
            ('develop', 'bugfix/tax', 'fix: correct tax'),
            ('develop', 'release/0.2.0', 'sync: forward-port QA fixes'),
            ('develop', 'sync/hotfix-021', 'sync(hotfix): apply production patch'),
            ('release/0.2.0', 'bugfix/qa', 'fix: QA issue'),
            ('hotfix/0.2.1', 'bugfix/urgent', 'fix: urgent patch'),
            ('release/0.3.0', 'sync/prod-fix', 'sync: forward-port production patch'),
            ('main', 'release/0.2.0', 'release: 0.2.0'),
            ('main', 'hotfix/0.2.1', 'fix: critical issue'),
        ]
        bad = [
            ('develop', 'feature/stock', 'chore: stock'),
            ('develop', 'release/0.2.0', 'fix: QA issue'),
            ('main', 'feature/stock', 'feat: stock'),
            ('main', 'release/0.2.0', 'release: 0.2.1'),
            ('release/0.2.0', 'feature/foo', 'feat: add foo'),
            ('hotfix/0.2.1', 'sync/prod-fix', 'sync: no QA sync on hotfix'),
        ]
        for case in good:
            with self.subTest(case=case): policy.validate(*case)
        for case in bad:
            with self.subTest(case=case):
                with self.assertRaises(ValueError): policy.validate(*case)
