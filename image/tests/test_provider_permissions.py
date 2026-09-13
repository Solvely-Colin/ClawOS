"""Provider wizard launchability must survive image normalization and install."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = '/usr/lib/clawos/clawos-provider-setup'
INSTALLER = ROOT / 'image/profile-overlay/airootfs/usr/local/bin/clawos-install-dev'


def executable_block():
    source = INSTALLER.read_text()
    start = source.index('chmod 0755 "$mount_root/usr/lib/clawos/clawos-session"')
    return source[start:].split('\n\n', 1)[0]


class ProviderPermissions(unittest.TestCase):
    def test_all_runtime_entrypoints_retain_executable_permissions(self):
        profile = (ROOT / 'image/profile-overlay/profiledef.sh').read_text()
        block = executable_block()
        directory = ROOT / 'image/profile-overlay/airootfs/usr/lib/clawos'
        # This package-list library is sourced by the installer, not executed.
        sourced_libraries = {'clawos-install-packages.sh'}
        for source in directory.iterdir():
            if not source.is_file() or source.name in sourced_libraries:
                continue
            if not source.read_bytes().startswith(b'#!'):
                continue
            path = '/usr/lib/clawos/' + source.name
            with self.subTest(entrypoint=source.name):
                self.assertTrue(f'"$mount_root{path}"' in block or
                                f'["{path}"]="0:0:755"' in profile,
                                f'{path} loses execute permission during image creation')

    def test_live_image_explicitly_preserves_executable_mode(self):
        profile = (ROOT / 'image/profile-overlay/profiledef.sh').read_text()
        self.assertIn(f'["{HELPER}"]="0:0:755"', profile)

    def test_installer_restores_provider_executable_mode(self):
        self.assertIn(f'"$mount_root{HELPER}"', executable_block())

    def test_installed_boot_requires_provider_launcher_marker(self):
        smoke = (ROOT / 'image/tests/install-smoke-qemu').read_text()
        self.assertIn(f'test -x {HELPER}; bash -n {HELPER}', smoke)
        loop = next(line for line in smoke.splitlines() if line.startswith('for marker in INSTALLED_ROOT_OK'))
        self.assertIn('PROVIDER_LAUNCHER_READY_OK', loop)

    @unittest.skipUnless(sys.platform == 'linux', 'Executes the real Bash chmod block')
    def test_real_installer_block_repairs_normalized_files(self):
        block = executable_block()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in set(re.findall(r'"\$mount_root(/[^"\n]+)"', block)) | {HELPER}:
                target = root / name.lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('#!/bin/sh\nexit 0\n')
                target.chmod(0o644)
            subprocess.run(['bash', '-eu', '-c', block], check=True,
                           env={**os.environ, 'mount_root': temporary})
            target = root / HELPER.lstrip('/')
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            subprocess.run([str(target)], check=True)


if __name__ == '__main__':
    unittest.main()
