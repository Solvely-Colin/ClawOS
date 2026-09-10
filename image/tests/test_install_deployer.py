"""Fresh installs must have a runnable updater and durable receipt delivery."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / 'image/profile-overlay/airootfs/usr/local/bin/clawos-install-dev'


class InstalledDeployer(unittest.TestCase):
    def test_live_profile_and_installed_timer_contract(self):
        profile = (ROOT / 'image/profile-overlay/profiledef.sh').read_text()
        self.assertIn('["/usr/lib/clawos/clawos-deploy"]="0:0:755"', profile)
        source = INSTALLER.read_text()
        enable = source[source.index('arch-chroot "$mount_root" systemctl enable'):]
        self.assertIn('clawos-deploy-delivery.timer', enable.split('arch-chroot "$mount_root" mkinitcpio')[0])
        smoke = (ROOT / 'image/tests/install-smoke-qemu').read_text()
        self.assertIn('DEPLOY_READY_OK', smoke)
        self.assertIn('test -x /usr/lib/clawos/clawos-deploy', smoke)

    @unittest.skipUnless(sys.platform == 'linux', 'Installer file modes require Linux')
    def test_provisioning_repairs_flattened_modes_and_installs_units(self):
        source = INSTALLER.read_text()
        start = source.index('install -m 0755 /usr/lib/clawos/clawos-deploy')
        end = source.index('install -m 0644 /usr/lib/tmpfiles.d/clawos-control.conf', start)
        fragment = source[start:end]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live, target = root / 'live', root / 'target'
            for base in (live, target):
                (base / 'usr/lib/clawos').mkdir(parents=True)
                (base / 'etc/systemd/system').mkdir(parents=True)
            files = ['usr/lib/clawos/clawos-deploy',
                     'etc/systemd/system/clawos-deploy-delivery.service',
                     'etc/systemd/system/clawos-deploy-delivery.timer']
            for name in files:
                (live / name).write_text('fixture\n')
                (live / name).chmod(0o644)
                fragment = fragment.replace(' /' + name, ' "$LIVE/' + name + '"')
            result = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + fragment],
                                    env={**os.environ, 'LIVE': str(live), 'mount_root': str(target)},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in files:
                installed = target / name
                self.assertEqual(installed.read_text(), 'fixture\n')
                self.assertEqual(stat.S_IMODE(installed.stat().st_mode),
                                 0o755 if name.endswith('/clawos-deploy') else 0o644)
