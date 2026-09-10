"""Repository entry points use components, not retired milestone directories."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ComponentLayout(unittest.TestCase):
    def test_no_tracked_milestone_directories(self):
        paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files'], text=True).splitlines()
        self.assertFalse([p for p in paths if p.split('/')[0] in {'m0', 'm1', 'm2', 'm3', 'm4', 'shell-prototype'}])

    def test_component_entry_points_exist(self):
        for path in (
            'image/bin/preflight-iso', 'image/bin/materialize-profile',
            'integrations/openclaw/index.js', 'services/clawosd/src/clawosd_core.py',
            'tests/integration/roles/role-switch.sh',
            'experiments/host-session/tests/static-check.sh',
        ):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_both_packagers_use_the_component_sources(self):
        for path in ('image/bin/materialize-profile',
                     'image/profile-overlay/airootfs/usr/lib/clawos/clawos-deploy'):
            text = (ROOT / path).read_text()
            for source in ('image/profile-overlay', 'integrations/openclaw', 'services/clawosd/src'):
                self.assertIn(source, text, path)
