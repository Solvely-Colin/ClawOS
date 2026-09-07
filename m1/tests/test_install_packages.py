import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'profile-overlay/airootfs/usr/lib/clawos/clawos-install-packages.sh'
INSTALLER = ROOT / 'profile-overlay/airootfs/usr/local/bin/clawos-install-dev'


class PackagePreparation(unittest.TestCase):
    def test_failure_ui_tracks_the_disk_write_marker(self):
        source = (ROOT / 'profile-overlay/airootfs/usr/lib/clawos/clawos-live-welcome').read_text()
        self.assertIn("line.strip() == 'CLAWOS_INSTALL_DISK_WRITE_STARTED'", source)
        self.assertIn('self._finish_install, code, passwordless, disk_write_started', source)
        self.assertIn('The target may be partially installed.', source)
        self.assertIn('The target disk was not changed.', source)

    def test_download_gate_precedes_disk_write_and_local_install(self):
        source = INSTALLER.read_text()
        self.assertLess(source.index('prepare_install_packages "$download_root"'), source.index('sfdisk --wipe'))
        self.assertLess(source.index('CLAWOS_INSTALL_DISK_WRITE_STARTED'), source.index('sfdisk --wipe'))
        self.assertIn('pacstrap -K -U -C "$download_root/local.conf"', source)
        self.assertNotIn('npm install --global', source)
        build = (ROOT / 'bin/build-iso').read_text()
        self.assertIn('npm install --global', build)
        self.assertIn('--prefix "$profile/airootfs/usr"', build)
        self.assertIn('"openclaw@$OPENCLAW_VERSION"', build)
        self.assertIn('usr/lib/node_modules/openclaw/package.json', (ROOT / 'tests/validate-iso.sh').read_text())
        self.assertIn('file_permissions[%q]', build)
        self.assertIn('mktemp -d /tmp/clawos-download.', source)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_retry_and_failure_are_bounded_before_install(self):
        for failures, expected_code, expected_attempts in [(0, 0, 1), (1, 0, 2), (3, 1, 3)]:
            with self.subTest(failures=failures), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(['bash', '-c', r'''
set -euo pipefail
source "$HELPER"
ARCH_SNAPSHOT=2026/08/25
attempts=0
timeout() {
  [[ "$1 $2" == '--kill-after=10s 15m' ]]
  attempts=$((attempts+1))
  if (( attempts <= FAILURES )); then return 1; fi
  printf package > "$STAGE/cache/base-1-any.pkg.tar.zst"
  printf signature > "$STAGE/cache/base-1-any.pkg.tar.zst.sig"
}
sleep() { :; }
pacman() { printf '%s\n' base-1-any.pkg.tar.zst; }
trap 'echo ATTEMPTS=$attempts' EXIT
prepare_install_packages "$STAGE"
[[ ${#install_files[@]} == 1 ]]
sha256sum -c --status "$STAGE/packages.sha256"
grep -Fx 'LocalFileSigLevel = Required' "$STAGE/local.conf"
'''], env={**os.environ, 'HELPER': str(HELPER), 'STAGE': tmp,
           'FAILURES': str(failures)}, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected_code, result.stderr + result.stdout)
                self.assertIn(f'ATTEMPTS={expected_attempts}', result.stdout)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_missing_signature_or_failed_resolution_refuses_preparation(self):
        for resolver in ['printf "base-1-any.pkg.tar.zst\\n"', 'return 1', 'printf "../escape.pkg.tar.zst\\n"']:
            with self.subTest(resolver=resolver), tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(['bash', '-c', r'''
set -euo pipefail
source "$HELPER"
ARCH_SNAPSHOT=2026/08/25
timeout() { printf package > "$STAGE/cache/base-1-any.pkg.tar.zst"; }
pacman() { eval "$RESOLVER"; }
prepare_install_packages "$STAGE"
'''], env={**os.environ, 'HELPER': str(HELPER), 'STAGE': tmp,
           'RESOLVER': resolver}, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
