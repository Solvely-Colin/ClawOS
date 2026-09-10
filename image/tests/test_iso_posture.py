"""ISO-side sshd posture and evidence-log hygiene.

validate-iso.sh asserts, on the built airootfs, that the ClawOS sshd drop-in
carries the three key-only directives and sorts ahead of archiso's
10-archiso.conf, that sshd_config includes the drop-in directory, and that
etc/issue still states the VM-only verification scope. Those checks are
functions that take an extracted tree, so this file runs them against fixture
trees without an ISO. boot-smoke-qemu and m2-e2e-qemu emit SSHD_KEYONLY_OK
from `sshd -T` inside the guest and run scan-log-secrets.sh over their
evidence before reporting success; the source assertions below keep those
hooks in place and the bash tests run the scanner against fixture logs.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_ISO = ROOT / 'tests/validate-iso.sh'
SCAN_LOG_SECRETS = ROOT / 'tests/scan-log-secrets.sh'
BOOT_SMOKE = ROOT / 'tests/boot-smoke-qemu'
M2_E2E = ROOT / 'tests/m2-e2e-qemu'
DROPIN = ROOT / 'profile-overlay/airootfs/etc/ssh/sshd_config.d/00-clawos.conf'
ISSUE = ROOT / 'profile-overlay/airootfs/etc/issue'

DIRECTIVES = ('PasswordAuthentication no', 'KbdInteractiveAuthentication no', 'PermitRootLogin no')
EFFECTIVE = tuple(directive.lower() for directive in DIRECTIVES)
BANNER = 'Verified only in virtual machines'
INCLUDE = 'Include /etc/ssh/sshd_config.d/*.conf'
ARCHISO_DROPIN = 'PermitRootLogin yes\nPasswordAuthentication yes\n'


def marker_loops(source):
    """Return the marker lists of every `for marker in ...; do` loop."""
    return [
        set(re.sub(r'\\\n', ' ', block).split())
        # Backslash-newline is already included in [^;]; a second matching
        # alternative makes malformed continued loops backtrack exponentially.
        for block in re.findall(r'for marker in([^;]*); do', source)
    ]


def write_fixture(root, dropin_name='00-clawos.conf', directives=DIRECTIVES,
                  archiso=True, include=True, banner=BANNER):
    root = Path(root)
    ssh = root / 'etc/ssh'
    (ssh / 'sshd_config.d').mkdir(parents=True)
    (ssh / 'sshd_config').write_text(
        ('# fixture\n' + INCLUDE + '\n' if include else '# fixture without Include\n') + 'AuthorizedKeysFile .ssh/authorized_keys\n')
    (ssh / 'sshd_config.d' / dropin_name).write_text('# ClawOS fixture\n' + ''.join(f'{line}\n' for line in directives))
    if archiso:
        (ssh / 'sshd_config.d/10-archiso.conf').write_text(ARCHISO_DROPIN)
    (ssh / 'sshd_config.d/99-archlinux.conf').write_text('KbdInteractiveAuthentication no\n')
    (root / 'etc/issue').write_text(f'ClawOS Live (experimental)\n\n{banner}. Recovery TTY: Ctrl+Alt+F3.\n')
    return root


def run_check(function, root):
    return subprocess.run(
        ['bash', '-c', 'set -euo pipefail; source "$VALIDATE_ISO"; "$1" "$2"', '_', function, str(root)],
        env={**os.environ, 'VALIDATE_ISO': str(VALIDATE_ISO)}, capture_output=True, text=True)


def run_scan(*files):
    return subprocess.run(['bash', str(SCAN_LOG_SECRETS), *map(str, files)], capture_output=True, text=True)


class MarkerLoops(unittest.TestCase):
    def test_multiple_loops_and_continuations(self):
        self.assertEqual(marker_loops('for marker in A ' + '\\\n' +
                                     ' B; do\ndone\nfor marker in C; do'),
                         [{'A', 'B'}, {'C'}])

    def test_malformed_continuations_finish_within_timeout(self):
        # Isolate the regression so an exponential match cannot hang the suite.
        program = (
            'import runpy\n'
            f'parse = runpy.run_path({str(Path(__file__).resolve())!r})["marker_loops"]\n'
            'for suffix in ("", "; not-do"):\n'
            '    assert parse("for marker in" + "\\\\\\n" * 64 + suffix) == []\n'
        )
        result = subprocess.run([sys.executable, '-c', program],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


class SourceHooks(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_effective_check_accepts_keyword_case_but_never_yes_or_missing(self):
        for script in (BOOT_SMOKE, M2_E2E):
            declarations = '\n'.join(line for line in script.read_text().splitlines()
                                     if line.startswith('sshd_keyonly_check=') or line.startswith('sshd_keyonly_check+='))
            fixtures = [('lower', '\n'.join(EFFECTIVE), 0),
                        ('canonical', '\n'.join(DIRECTIVES), 0),
                        ('upper', '\n'.join(DIRECTIVES).upper(), 0)]
            for index in range(3):
                weakened = list(DIRECTIVES)
                weakened[index] = weakened[index].replace(' no', ' yes')
                fixtures.append((f'weakened-{index}', '\n'.join(weakened), 1))
                fixtures.append((f'missing-{index}', '\n'.join(DIRECTIVES[:index] + DIRECTIVES[index+1:]), 1))
            for label, output, expected in fixtures:
                with self.subTest(script=script.name, fixture=label), tempfile.TemporaryDirectory() as tmp:
                    program = ('set -euo pipefail\n'
                               'systemctl() { return 0; }\n'
                               'sshd() { printf "%s\\n" "$SSHD_OUTPUT"; }\n' +
                               declarations.replace('/tmp/sshd-effective.conf', str(Path(tmp)/'effective.conf')) +
                               '\neval "$sshd_keyonly_check"\n')
                    result = subprocess.run(['bash', '-c', program],
                                            env={**os.environ, 'SSHD_OUTPUT': output}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stderr)

    def test_validate_iso_extracts_and_checks_the_shipped_sshd_files(self):
        source = VALIDATE_ISO.read_text()
        self.assertIn('etc/ssh/sshd_config etc/ssh/sshd_config.d etc/issue', source)
        self.assertIn('check_sshd_posture "$posture"', source)
        self.assertIn('check_live_banner "$posture"', source)
        self.assertIn('10-archiso.conf', source)
        self.assertIn("'Verified only in virtual machines'", source)
        self.assertIn('grep -Fqx "$directive"', source)
        for directive in DIRECTIVES:
            self.assertIn(f"'{directive}'", source)

    def test_overlay_dropin_and_banner_are_what_the_iso_check_expects(self):
        lines = DROPIN.read_text().splitlines()
        for directive in DIRECTIVES:
            self.assertIn(directive, lines, f'{DROPIN} must carry the exact line {directive!r}')
        self.assertIn(BANNER, ISSUE.read_text())

    def test_qemu_gates_emit_sshd_keyonly_from_sshd_dash_t(self):
        for script, markers in ((BOOT_SMOKE, ['SSHD_KEYONLY_OK']),
                                (M2_E2E, ['SSHD_KEYONLY_OK', 'INSTALLED_SSHD_KEYONLY_OK'])):
            with self.subTest(script=script.name):
                source = script.read_text()
                self.assertIn('sshd -T >/tmp/sshd-effective.conf', source)
                for setting in EFFECTIVE:
                    self.assertIn(f'grep -Fqxi "{setting}" /tmp/sshd-effective.conf', source)
                loops = marker_loops(source)
                for marker in markers:
                    self.assertIn(f'echo "${{PASS}}{marker}"', source)
                    self.assertTrue(any(marker in loop for loop in loops), f'{marker} is not required by a marker loop')

    def test_boot_smoke_markers_cannot_be_satisfied_by_the_echoed_command(self):
        source = BOOT_SMOKE.read_text()
        self.assertIn("commands=$'\\nPASS=PASS:\\n'", source)
        self.assertIn('grep -Fq "PASS:$marker" "$transcript"', source)
        self.assertNotRegex(source, r'echo [A-Z_]+_OK\b')

    def test_qemu_gates_scan_their_evidence_before_success(self):
        smoke = BOOT_SMOKE.read_text()
        self.assertIn('"$repo_root/image/tests/scan-log-secrets.sh" "$serial_log" "$transcript" "$qemu_log"', smoke)
        self.assertLess(smoke.index('scan-log-secrets.sh'), smoke.index('boot smoke test passed'))
        e2e = M2_E2E.read_text()
        self.assertIn('"$repo_root/image/tests/scan-log-secrets.sh" "$runtime"/*-serial.log "$runtime"/*-qemu.log', e2e)
        self.assertLess(e2e.index('scan-log-secrets.sh'), e2e.index('QEMU validation passed'))


@unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
class PostureFunctions(unittest.TestCase):
    def test_shipped_layout_passes_and_reports_the_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_sshd_posture', write_fixture(tmp))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('00-clawos.conf sorts ahead of 10-archiso.conf', result.stdout)
            self.assertEqual(run_check('check_live_banner', tmp).returncode, 0)

    def test_dropin_renamed_after_archiso_fails_on_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_sshd_posture', write_fixture(tmp, dropin_name='20-clawos.conf'))
            self.assertEqual(result.returncode, 1)
            self.assertIn('20-clawos.conf sorts after 10-archiso.conf', result.stderr)

    def test_missing_archiso_dropin_fails_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_sshd_posture', write_fixture(tmp, archiso=False))
            self.assertEqual(result.returncode, 1)
            self.assertIn('10-archiso.conf is missing', result.stderr)

    def test_dropin_that_sorts_first_but_is_not_the_installer_copy_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_sshd_posture', write_fixture(tmp, dropin_name='05-clawos.conf'))
            self.assertEqual(result.returncode, 1)
            self.assertIn('clawos-install-dev copies 00-clawos.conf', result.stderr)

    def test_each_directive_is_required_as_an_exact_line(self):
        for missing in DIRECTIVES:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                weakened = tuple(f'# {d}' if d == missing else d for d in DIRECTIVES)
                result = run_check('check_sshd_posture', write_fixture(tmp, directives=weakened))
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"00-clawos.conf lacks the line '{missing}'", result.stderr)

    def test_sshd_config_without_the_include_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_sshd_posture', write_fixture(tmp, include=False))
            self.assertEqual(result.returncode, 1)
            self.assertIn('does not Include /etc/ssh/sshd_config.d/*.conf', result.stderr)

    def test_banner_without_the_scope_statement_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check('check_live_banner', write_fixture(tmp, banner='Ready for production'))
            self.assertEqual(result.returncode, 1)
            self.assertIn("etc/issue no longer says 'Verified only in virtual machines'", result.stderr)


@unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
class SecretScan(unittest.TestCase):
    CLEAN = (
        'clawos-live# PASS=PASS:\n'
        'PASS:__CLAWOS_SMOKE_BEGIN__\n'
        'clawos-live# sshd -T >/tmp/sshd-effective.conf && grep -Fqx "passwordauthentication no" /tmp/sshd-effective.conf\n'
        'PASS:SSHD_KEYONLY_OK\n'
        'PASS:M3_AUDIT_TOKEN_SAFE_OK\n'
        'systemd-cryptsetup[312]: Set cipher aes, mode xts-plain64, key size 512 bits for device /dev/vda2.\n'
        'Please enter passphrase for disk vda2 (cryptroot):\n'
        'disk-safety: identity rechecked\n'
        '{"securityLevel":"full-root"}\n'
    )

    def test_clean_evidence_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, 'serial.log')
            log.write_bytes(b'\x00\x00' + self.CLEAN.encode())
            result = run_scan(log)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no secret-shaped strings in 1 file(s).', result.stdout)

    def test_findings_name_the_pattern_and_line_but_not_the_text(self):
        # Assembled at runtime so this file never contains a secret-shaped literal.
        key_header = '-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'
        token_json = '{"' + 'token":"' + 'a1b2c3d4e5f6g7h8' + '"}'
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, 'transcript.log')
            log.write_text(self.CLEAN + key_header + '\nfiller\n' + token_json + '\n')
            result = run_scan(log)
            self.assertEqual(result.returncode, 1)
            clean_lines = self.CLEAN.count('\n')
            self.assertIn(f'private-key-block pattern at line(s) {clean_lines + 1}', result.stderr)
            self.assertIn(f'credential-assignment pattern at line(s) {clean_lines + 3}', result.stderr)
            self.assertNotIn('OPENSSH', result.stderr + result.stdout)
            self.assertNotIn('a1b2c3d4', result.stderr + result.stdout)
            self.assertIn('refusing to publish', result.stderr)

    def test_word_anchored_sk_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean = Path(tmp, 'clean.log')
            clean.write_text('disk-safety-check-passed-0123456789\n')
            self.assertEqual(run_scan(clean).returncode, 0)
            leaked = Path(tmp, 'leaked.log')
            leaked.write_text('key=' + 'sk-' + 'ant-api03-0123456789abcdef\n')
            result = run_scan(leaked)
            self.assertEqual(result.returncode, 1)
            self.assertIn('sk-prefixed-api-key pattern at line(s) 1', result.stderr)

    def test_missing_file_is_an_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_scan(Path(tmp, 'absent.log')).returncode, 2)
            self.assertEqual(run_scan().returncode, 2)


if __name__ == '__main__':
    unittest.main()
