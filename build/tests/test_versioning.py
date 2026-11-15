import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from versioning import Version, bump, change_type, next_dev, unpublished_change_type
from validate_pr import validate


class VersioningTests(unittest.TestCase):
    def test_first_feature(self):
        self.assertEqual(next_dev(Version(0, 0, 0), None, "feat"), (Version(0, 1, 0), 1))

    def test_fix_inside_unreleased_minor_does_not_bump_patch(self):
        self.assertEqual(next_dev(Version(1, 0, 0), (Version(1, 1, 0), 3), "fix"), (Version(1, 1, 0), 4))

    def test_hotfix_on_main_does_not_downgrade_develop(self):
        self.assertEqual(next_dev(Version(1, 0, 1), (Version(1, 1, 0), 3), "fix"), (Version(1, 1, 0), 4))

    def test_after_release_new_feature_starts_new_minor(self):
        self.assertEqual(next_dev(Version(1, 1, 0), (Version(1, 1, 0), 3), "feat"), (Version(1, 2, 0), 1))

    def test_breaking_change(self):
        self.assertEqual(change_type("feat!: incompatible API"), "breaking")
        self.assertEqual(bump(Version(1, 2, 3), "breaking"), Version(2, 0, 0))

    def test_merge_commit_body_feature(self):
        message = "Merge pull request #7 from owner/feature/inventory\n\nfeat: Add Inventory and order service"
        self.assertEqual(change_type(message), "feat")

    def test_chore_does_not_bump_patch(self):
        self.assertEqual(change_type("chore: simplify README"), "none")
        self.assertEqual(bump(Version(0, 0, 0), "none"), Version(0, 0, 0))

    def test_accumulated_feature_after_chore(self):
        # History contains a feature even if the latest merge is a chore.
        import subprocess, tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(["git", "-C", directory, *args], text=True).strip()
            git("init", "-q", "-b", "develop")
            git("config", "user.email", "test@example.org")
            git("config", "user.name", "Tests")
            from pathlib import Path
            f = Path(directory) / "file.txt"
            f.write_text("first")
            git("add", ".")
            git("commit", "-qm", "feat: add inventory")
            f.write_text("second")
            git("commit", "-qam", "chore: update readme")
            with patch("versioning.run", side_effect=git):
                self.assertEqual(unpublished_change_type(git("rev-parse", "HEAD"), None), "feat")

    def test_conventional_title(self):
        validate("develop", "feature/discount", "feat: add discount")
        with self.assertRaises(ValueError):
            validate("main", "feature/discount", "feat: add discount")


if __name__ == "__main__":
    unittest.main()
