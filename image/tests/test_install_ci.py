import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('qemu_io_install', ROOT / 'tools/ci/qemu_io.py')
qemu_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qemu_io)


class InstallCI(unittest.TestCase):
    def test_installed_console_cannot_match_live_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'log'
            log.write_text('clawos-live# ')
            self.assertFalse(qemu_io.console_ready(log, 'clawos-installed'))
            log.write_text('root@clawos-installed ~ # ')
            self.assertTrue(qemu_io.console_ready(log, 'clawos-installed'))
            self.assertFalse(qemu_io.console_ready(log))

    def test_new_disk_identity_and_disk_only_reboot_contract(self):
        source = (ROOT / 'image/tests/install-smoke-qemu').read_text()
        self.assertIn('mkdir "$runtime" # Existing', source)
        self.assertIn('qemu-img create -f qcow2 "$disk" 32G', source)
        self.assertIn('serial=CLAWOS-SMOKE-DISK', source)
        self.assertIn('cat /sys/block/vda/serial', source)
        self.assertIn('--disk-id "$disk_id" --confirm ERASE-/dev/vda', source)
        self.assertIn('--vm-test --passwordless', source)
        launches = [line for line in source.splitlines() if line.startswith('start_guest ')]
        self.assertEqual(launches, ['start_guest live -cdrom "$iso" -boot d', 'start_guest installed -boot c'])
        self.assertIn('findmnt -no SOURCE /', source)
        self.assertIn('grep -Fxq "PASS:$marker"', source)
        for line in source.splitlines():
            if 'kill ' in line:
                self.assertIn('kill -0 ', line)
        self.assertNotIn('kill-after', source)
        self.assertIn('qemu_io.py" powerdown', source)

    def test_upload_whitelist_excludes_disk_and_firmware(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text()
        whitelist = next(line for line in workflow.splitlines() if 'for name in live-serial.log' in line)
        for forbidden in ('qcow2', 'vars.fd', '*.log', '*;'):
            self.assertNotIn(forbidden, whitelist)
        self.assertIn('installed.ppm', whitelist)
        self.assertLess(workflow.index('scan-log-secrets.sh "$source"'), workflow.index('cp "$source" artifacts/boot-evidence/install/'))

    def test_uart_input_is_paced_without_losing_bytes(self):
        class Serial:
            def __init__(self): self.sent = []
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def settimeout(self, timeout): pass
            def connect(self, path): pass
            def sendall(self, data): self.sent.append(data)
            def recv(self, size): return b'DONE:INSTALL\r\n'
        serial = Serial()
        commands = b'x' * 1500
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(qemu_io.socket, 'AF_UNIX', 1, create=True), \
                patch.object(qemu_io.socket, 'socket', return_value=serial), \
                patch.object(qemu_io.time, 'sleep') as pause:
            qemu_io.capture('/test/socket', Path(tmp) / 'log', commands, 5, 'DONE:INSTALL')
        self.assertEqual(b''.join(serial.sent), commands)
        self.assertTrue(all(len(chunk) <= 64 for chunk in serial.sent))
        self.assertEqual(pause.call_count, len(serial.sent))

    @unittest.skipUnless(sys.platform == 'linux', 'Shell contract runs on Linux CI')
    def test_guest_already_exited_is_not_an_acpi_success(self):
        source = (ROOT / 'image/tests/install-smoke-qemu').read_text()
        function = source[source.index('shutdown_guest() {'):source.index('\nfinish() {')]
        fixture = 'kill() { return 1; }; wait() { return 0; }; qemu_pid=123\n'
        result = subprocess.run(['bash', '-c', fixture + function + '\nshutdown_guest'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn('before the required ACPI', result.stderr)

    @unittest.skipUnless(sys.platform == 'linux', 'Shell contract runs on Linux CI')
    def test_wrong_guest_disk_stops_before_installer_and_still_completes(self):
        source = (ROOT / 'image/tests/install-smoke-qemu').read_text()
        payload = next(line for line in source.splitlines() if line.startswith("bash -c '"))
        # Only the read-only preconditions run. A wrong serial must prevent
        # both inventory and installer execution, without hiding completion.
        fixture = ('findmnt() { echo overlay; }; cat() { echo WRONG-DISK; }; '
                   'python3() { echo UNEXPECTED-INVENTORY; }; '
                   'clawos-install-dev() { echo UNEXPECTED-INSTALLER; }; '
                   'export -f findmnt cat python3 clawos-install-dev\n')
        result = subprocess.run(['bash', '-c', fixture + payload + '\nD=DONE:; echo "${D}INSTALL"\n'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.stdout, 'DONE:INSTALL\n', result.stderr)
        self.assertNotIn('PASS:INSTALL_OK', result.stdout)

    @unittest.skipUnless(sys.platform == 'linux', 'Shell contract runs on Linux CI')
    def test_install_metadata_cannot_mask_failure(self):
        helper = (ROOT / 'tools/ci/build-release.sh').read_text()
        fragment = helper[helper.index('# Fresh disposable disk'):]
        for status in (0, 23):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                smoke = root / 'image/tests/install-smoke-qemu'
                smoke.parent.mkdir(parents=True)
                smoke.write_text('#!/usr/bin/env bash\nexit "$SMOKE_EXIT"\n')
                smoke.chmod(0o755)
                out = root / 'out'
                out.mkdir()
                metadata = out / 'BUILD-METADATA.txt'
                metadata.write_text('Passwordless install smoke: NOT RUN\nOnboarding: NOT RUN\n')
                result = subprocess.run(['bash', '-c', 'set -euo pipefail\nout="$CASE_OUT"\nimages=(fixture.iso)\n' + fragment],
                                        cwd=root, env={**os.environ, 'CASE_OUT': str(out),
                                        'GITHUB_RUN_ID': '42', 'SMOKE_EXIT': str(status)},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                outcome = 'RUN' if status == 0 else 'FAILED'
                self.assertEqual(metadata.read_text(), f'Passwordless install smoke: {outcome} (KVM, run 42)\nOnboarding: NOT RUN\n')
