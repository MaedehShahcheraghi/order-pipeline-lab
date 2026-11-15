import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from versioning import Version, bump, change_type, next_dev
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

    def test_conventional_title(self):
        validate("develop", "feature/discount", "feat: add discount")
        with self.assertRaises(ValueError):
            validate("main", "feature/discount", "feat: add discount")


if __name__ == "__main__":
    unittest.main()
