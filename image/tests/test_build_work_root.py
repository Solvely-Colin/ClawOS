from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class BuildWorkRootTests(unittest.TestCase):
    def test_override_is_canonical_and_cleanup_stays_under_fixed_basenames(self):
        source = (ROOT / "image/bin/build-iso").read_text()
        self.assertIn("work_root=${CLAWOS_BUILD_WORK_ROOT:-/var/tmp}", source)
        self.assertIn('"$work_root" != /*', source)
        self.assertIn('! -d "$work_root"', source)
        self.assertIn('-L "$work_root"', source)
        self.assertIn('"$(realpath -e -- "$work_root")" != "$work_root"', source)
        self.assertIn('work="$work_root/clawos-m1-work-fast"', source)
        self.assertIn('work="$work_root/clawos-m1-work"', source)
        self.assertNotIn('work="/var/tmp/clawos-m1-work', source)
        self.assertIn('find "$generated_dir" -depth -delete', source)


if __name__ == "__main__":
    unittest.main()
