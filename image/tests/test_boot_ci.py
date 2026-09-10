import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('qemu_io', ROOT / 'tools/ci/qemu_io.py')
qemu_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qemu_io)


class FakeSocket:
    def __init__(self, replies=(), chunks=()):
        self.replies = list(replies)
        self.chunks = list(chunks)
        self.sent = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def settimeout(self, value): pass
    def connect(self, path): self.path = path
    def makefile(self, mode): return self
    def readline(self): return self.replies.pop(0) if self.replies else b''
    def write(self, value): self.sent.append(json.loads(value))
    def flush(self): pass
    def sendall(self, value): self.commands = value
    def recv(self, size): return self.chunks.pop(0) if self.chunks else b''


class BootCI(unittest.TestCase):
    def setUp(self):
        unix = patch.object(qemu_io.socket, 'AF_UNIX', 1, create=True)
        unix.start()
        self.addCleanup(unix.stop)

    def test_console_readiness_accepts_plain_and_colored_root_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'serial.log'
            for text, ready in [('Booting kernel\nclawos-live login:', False),
                                ('clawos-live# ', True),
                                ('\x1b[31mroot\x1b[0m@\x1b[32mclawos-live\x1b[0m ~ # ', True)]:
                log.write_text(text)
                self.assertEqual(qemu_io.console_ready(log), ready)

    def test_qmp_sends_only_capabilities_and_acpi(self):
        fake = FakeSocket([b'{"QMP":{}}\n', b'{"event":"STOP"}\n',
                           b'{"id":"qmp_capabilities","return":{}}\n',
                           b'{"id":"system_powerdown","return":{}}\n'])
        with patch.object(qemu_io.socket, 'socket', return_value=fake):
            qemu_io.powerdown('/test/qmp.sock')
        self.assertEqual([p['execute'] for p in fake.sent], ['qmp_capabilities', 'system_powerdown'])

    def test_qmp_eof_and_rejection_fail(self):
        for response in (b'', b'{"id":"qmp_capabilities","error":{"class":"GenericError"}}\n'):
            with self.subTest(response=response):
                fake = FakeSocket([b'{"QMP":{}}\n', response])
                with patch.object(qemu_io.socket, 'socket', return_value=fake):
                    with self.assertRaises(ValueError):
                        qemu_io.powerdown('/test/qmp.sock')

    def test_serial_captures_until_guest_disconnect(self):
        fake = FakeSocket(chunks=[b'PASS:IDENTITY_OK\r\n', b'PASS:END\r\n'])
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'serial.log'
            with patch.object(qemu_io.socket, 'socket', return_value=fake):
                qemu_io.capture('/test/serial.sock', log, b'poweroff\n', 5)
            self.assertEqual(fake.commands, b'poweroff\n')
            self.assertEqual(log.read_bytes(), b'PASS:IDENTITY_OK\r\nPASS:END\r\n')

    def test_serial_deadline_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(qemu_io.socket, 'socket', return_value=FakeSocket()), \
                    patch.object(qemu_io.time, 'monotonic', side_effect=[0, 6]):
                with self.assertRaises(TimeoutError):
                    qemu_io.capture('/test/socket', Path(tmp) / 'out', b'x', 5)

    def test_serial_completion_marker_can_span_reads(self):
        fake = FakeSocket(chunks=[b'echo "${PASS}END"\r\nPASS:E', b'ND\r\n', b'after'])
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(qemu_io.socket, 'socket', return_value=fake):
            qemu_io.capture('/test/socket', Path(tmp) / 'out', b'commands', 5, 'PASS:END')
        self.assertEqual(fake.chunks, [b'after'])

    def test_echoed_marker_and_early_eof_do_not_complete_capture(self):
        fake = FakeSocket(chunks=[b'echo "${PASS}END"\r\n'])
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(qemu_io.socket, 'socket', return_value=fake):
            with self.assertRaises(ValueError):
                qemu_io.capture('/test/socket', Path(tmp) / 'out', b'commands', 5, 'PASS:END')

    def test_workflow_requires_kvm_and_gates_uploads(self):
        workflow = (ROOT / '.github/workflows/release.yml').read_text()
        self.assertLess(workflow.index('Probe KVM'), workflow.index('Build in disposable'))
        self.assertIn('--device /dev/kvm', workflow)
        self.assertIn('test -r /dev/kvm && test -w /dev/kvm', workflow)
        self.assertIn('${RUNNER_ENVIRONMENT:-}', workflow)
        self.assertLess(workflow.index('99-kvm4all.rules'), workflow.index('test -c /dev/kvm'))
        self.assertIn('inputs.retain_iso', workflow)
        self.assertIn("steps.evidence.outputs.safe == 'true'", workflow)
        self.assertIn('default: false', workflow)
        self.assertNotIn('path: artifacts/m1/out/*', workflow)
        helper = (ROOT / 'tools/ci/build-release.sh').read_text()
        self.assertLess(helper.index('./image/tests/boot-smoke-qemu'), helper.index('Live boot smoke: RUN (KVM'))
        self.assertIn('Onboarding/encrypted-install/hardware acceptance: NOT RUN', helper)
        self.assertIn('Live boot smoke: FAILED (KVM', helper)

    @unittest.skipUnless(sys.platform == 'linux', 'Shell contract runs on Linux CI')
    def test_metadata_records_success_and_failure_without_masking_exit(self):
        helper = (ROOT / 'tools/ci/build-release.sh').read_text()
        fragment = helper[helper.index('# Same freshly built ISO'):helper.index('# Fresh disposable disk')]
        for status in (0, 23):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                smoke = root / 'image/tests/boot-smoke-qemu'
                smoke.parent.mkdir(parents=True)
                smoke.write_text('#!/usr/bin/env bash\nexit "$SMOKE_EXIT"\n')
                smoke.chmod(0o755)
                out = root / 'out'
                out.mkdir()
                (out / 'fixture.iso').write_bytes(b'fixture')
                metadata = out / 'BUILD-METADATA.txt'
                metadata.write_text('Live boot smoke: NOT RUN\nInstall acceptance: NOT RUN\n')
                result = subprocess.run(['bash', '-c', 'set -euo pipefail\nout="$CASE_OUT"\n' + fragment],
                                        cwd=root, env={**os.environ, 'CASE_OUT': str(out),
                                        'GITHUB_RUN_ID': '42', 'SMOKE_EXIT': str(status)},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                outcome = 'RUN' if status == 0 else 'FAILED'
                self.assertEqual(metadata.read_text(),
                                 f'Live boot smoke: {outcome} (KVM, run 42)\nInstall acceptance: NOT RUN\n')

    def test_smoke_has_no_process_termination_and_uses_exact_markers(self):
        source = (ROOT / 'image/tests/boot-smoke-qemu').read_text()
        for line in source.splitlines():
            if 'kill ' in line:
                self.assertIn('kill -0 ', line)
        self.assertNotIn('enp0s1', source)
        self.assertIn('qemu_io.py" powerdown', source)
        self.assertNotIn("commands+=$'poweroff", source)
        self.assertIn('grep -Fxq "PASS:$marker"', source)
        self.assertIn('CLAWOS_OVMF_CODE', source)
        self.assertIn('CLAWOS_SMOKE_DEADLINE', source)
