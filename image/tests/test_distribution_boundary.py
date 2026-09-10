"""No foreign-distribution references outside explicit negative-test data."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'image/tests/check-distribution-boundary.sh'
FORBIDDEN = (b'omarchy', b'omacom', b'omakub')
NEGATIVE_CHECKS = {
    'image/tests/check-distribution-boundary.sh',
    'image/tests/validate-profile.sh',
    'image/tests/test_distribution_boundary.py',
}


class DistributionBoundary(unittest.TestCase):
    def test_tracked_content_and_paths_have_no_foreign_distribution_references(self):
        tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'])
        failures = []
        for raw in tracked.split(b'\0'):
            if not raw:
                continue
            name = raw.decode('utf-8')
            if name in NEGATIVE_CHECKS:
                continue
            data = (ROOT / name).read_bytes().lower()
            if any(token in raw.lower() or token in data for token in FORBIDDEN):
                failures.append(name)
        self.assertEqual(failures, [], 'References are allowed only as explicit negative-check data')

    @unittest.skipUnless(sys.platform == 'linux', 'Root-tree fixture uses Linux shell tools')
    def test_generated_root_rejects_paths_policies_and_dangling_links(self):
        cases = [
            ('clean', None, 0),
            ('usr/share/omarchy', b'fixture', 1),
            ('etc/systemd/system/fixture.service', b'ExecStart=/usr/bin/OMARCHY-launch\n', 1),
            ('etc/pacman.d/fixture', b'Server = https://packages.omacom.example/repo\n', 1),
            ('etc/omarchy', 'dangling-link', 1),
        ]
        for name, content, expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                if content is not None:
                    path = root / name
                    path.parent.mkdir(parents=True)
                    if content == 'dangling-link':
                        path.symlink_to(root / 'missing')
                    else:
                        path.write_bytes(content)
                result = subprocess.run(['bash', str(GUARD), str(root)],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stderr)
