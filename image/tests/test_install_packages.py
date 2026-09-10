import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'profile-overlay/airootfs/usr/lib/clawos/clawos-install-packages.sh'
INSTALLER = ROOT / 'profile-overlay/airootfs/usr/local/bin/clawos-install-dev'

# Shared preamble for the Bash behavior tests: the real helper, the pinned
# snapshot, and stand-ins for every live probe so nothing touches the network,
# /proc or df. Tests override individual functions after this prefix.
PREAMBLE = r'''
set -euo pipefail
source "$HELPER"
ARCH_SNAPSHOT=2026/08/25
GiB=$((1024 * 1024 * 1024))
curl() { printf 200; }
tmp_available_bytes() { echo $((4 * GiB)); }
memory_available_bytes() { echo $((3 * GiB)); }
sleep() { :; }
attempts=0
pacman_calls=0
pacman() {
  pacman_calls=$((pacman_calls + 1))
  case " $* " in
    *' -Sy '*) : ;;
    *'%s'*) printf '%s\n' $((SIZE_BYTES / 2)) $((SIZE_BYTES - SIZE_BYTES / 2)) ;;
    *'%f'*) printf '%s\n' base-1-any.pkg.tar.zst ;;
  esac
}
timeout() {
  case "$1 $2" in
    '--kill-after=10s 5m') shift 2; "$@"; return ;;
    '--kill-after=10s 15m') ;;
    *) echo "unexpected timeout arguments: $*" >&2; return 99 ;;
  esac
  attempts=$((attempts + 1))
  if (( attempts <= FAILURES )); then echo "error: failed retrieving file 'x' from archive.archlinux.org : $FAILURE_TEXT" >&2; return 1; fi
  printf package > "$STAGE/cache/base-1-any.pkg.tar.zst"
  printf signature > "$STAGE/cache/base-1-any.pkg.tar.zst.sig"
}
trap 'echo ATTEMPTS=$attempts PACMAN_CALLS=$pacman_calls' EXIT
'''


def run_bash(script, stdin='', **env):
    defaults = {'HELPER': str(HELPER), 'FAILURES': '0', 'FAILURE_TEXT': '', 'SIZE_BYTES': str(1024 ** 3)}
    return subprocess.run(['bash', '-c', PREAMBLE + script], input=stdin,
                          env={**os.environ, **defaults, **env}, capture_output=True, text=True)


def last_line(text):
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ''


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

    def test_preflight_guards_run_before_any_package_download(self):
        # Reachability, database refresh, size arithmetic, then the download;
        # all of it inside prepare_install_packages, which the installer runs
        # before its disk-write marker. The checksum recheck that follows must
        # not exit silently either.
        helper = HELPER.read_text()
        order = ['probe_archive "$stage"', "'Refreshing the pinned package databases'", "--print-format '%s'",
                 'check_download_capacity "$size"', "'Downloading and verifying installation packages'", '-Syw']
        positions = [helper.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions), order)
        self.assertIn('increase VM memory to at least 4 GiB', helper)
        self.assertIn('--max-time 10', helper)
        self.assertIn("timeout --kill-after=10s \"$deadline\" pacman", helper)
        installer = INSTALLER.read_text()
        self.assertLess(installer.index('prepare_install_packages "$download_root"'),
                        installer.index('CLAWOS_INSTALL_DISK_WRITE_STARTED'))
        self.assertIn('sha256sum --check --status "$download_root/packages.sha256" || {', installer)
        self.assertLess(installer.index('the prepared packages changed after verification'),
                        installer.index('CLAWOS_INSTALL_DISK_WRITE_STARTED'))

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_retry_only_after_timeouts_or_resets_and_stop_on_everything_else(self):
        cases = [
            ('', 0, 0, 1, None),
            ('Recv failure: Connection reset by peer', 1, 0, 2, None),
            ('Operation timed out after 30000 milliseconds with 0 bytes received', 2, 0, 3, None),
            ('HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)', 3, 1, 3, 'reset mid-transfer'),
            ('Could not resolve host: archive.archlinux.org', 3, 1, 1, 'could not be resolved (DNS)'),
            ('Failed to connect to archive.archlinux.org port 443: Connection refused', 3, 1, 1, 'refused or the host is unreachable'),
            ('SSL certificate problem: unable to get local issuer certificate', 3, 1, 1, 'TLS connection'),
            ('The requested URL returned error: 503', 3, 1, 1, 'HTTP 503'),
            ('No space left on device', 3, 1, 1, 'increase VM memory to at least 4 GiB'),
            ('something the installer has never seen', 3, 1, 1, 'does not classify'),
        ]
        for text, failures, expected_code, expected_attempts, expected_reason in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                result = run_bash(r'''
prepare_install_packages "$STAGE"
[[ ${#install_files[@]} == 1 ]]
sha256sum -c --status "$STAGE/packages.sha256"
grep -Fx 'LocalFileSigLevel = Required' "$STAGE/local.conf"
''', STAGE=tmp, FAILURES=str(failures), FAILURE_TEXT=text)
                self.assertEqual(result.returncode, expected_code, result.stderr + result.stdout)
                self.assertIn(f'ATTEMPTS={expected_attempts} ', result.stdout)
                if expected_reason:
                    final = last_line(result.stderr)
                    self.assertTrue(final.startswith('Package preparation failed: '), final)
                    self.assertTrue(final.endswith(' The target disk has not been changed.'), final)
                    self.assertIn(expected_reason, final)
                    self.assertIn(text, result.stderr)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_unreachable_archive_stops_before_pacman_runs(self):
        cases = [
            ('return 6', 'could not be resolved (DNS)'),
            ('return 7', 'refused or the host is unreachable'),
            ('return 28', 'did not answer within the deadline'),
            ('return 60', 'TLS connection'),
            ('printf 302', 'captive portal or proxy is intercepting'),
            ('printf 404', 'Check ARCH_SNAPSHOT in versions.env'),
            ('printf 503', 'temporarily unavailable'),
        ]
        for curl_body, expected_reason in cases:
            with self.subTest(curl=curl_body), tempfile.TemporaryDirectory() as tmp:
                result = run_bash(f'curl() {{ {curl_body}; }}\nprepare_install_packages "$STAGE"\n', STAGE=tmp)
                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                self.assertIn('ATTEMPTS=0 PACMAN_CALLS=0', result.stdout)
                final = last_line(result.stderr)
                self.assertTrue(final.startswith('Package preparation failed: '), final)
                self.assertIn(expected_reason, final)
                self.assertTrue(final.endswith(' The target disk has not been changed.'), final)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_insufficient_live_storage_or_memory_stops_before_download(self):
        # 1.5 GiB of packages against a 2 GiB VM: /tmp is half of RAM.
        cases = [
            ('tmp_available_bytes() { echo $((GiB)); }', 'but /tmp has 1024 MiB free'),
            ('memory_available_bytes() { echo $((GiB)); }', 'only 1024 MiB is available'),
        ]
        for override, expected in cases:
            with self.subTest(override=override), tempfile.TemporaryDirectory() as tmp:
                result = run_bash(override + '\nprepare_install_packages "$STAGE"\n',
                                  STAGE=tmp, SIZE_BYTES=str(3 * 1024 ** 3 // 2))
                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                self.assertIn('ATTEMPTS=0 ', result.stdout)
                final = last_line(result.stderr)
                self.assertIn('increase VM memory to at least 4 GiB', final)
                self.assertIn(expected, final)
                self.assertTrue(final.endswith(' The target disk has not been changed.'), final)
        with tempfile.TemporaryDirectory() as tmp:
            # A disk-backed /tmp reports no memory figure and is not held to one.
            result = run_bash('memory_available_bytes() { :; }\nprepare_install_packages "$STAGE"\n',
                              STAGE=tmp, SIZE_BYTES=str(3 * 1024 ** 3 // 2))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn('Download size 1536 MiB; free temporary storage 4096 MiB.', result.stdout)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_capacity_arithmetic_includes_the_margin(self):
        mib = 1024 ** 2
        cases = [
            (1000 * mib, 1256 * mib, '', 0),
            (1000 * mib, 1255 * mib, '', 1),
            (1000 * mib, 4096 * mib, 1256 * mib, 0),
            (1000 * mib, 4096 * mib, 1255 * mib, 1),
            (0, 256 * mib, '', 0),
            (0, 256 * mib - 1, '', 1),
        ]
        for size, free, memory, expected_code in cases:
            with self.subTest(size=size, free=free, memory=memory):
                result = run_bash(f'check_download_capacity {size} {free} "{memory}"\n')
                self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
                if expected_code:
                    self.assertIn('needs 1256 MiB' if size else 'needs 256 MiB', result.stdout)
                    self.assertIn('increase VM memory to at least 4 GiB', result.stdout)
                else:
                    self.assertEqual(result.stdout.strip().splitlines(), ['ATTEMPTS=0 PACMAN_CALLS=0'])

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_download_size_sum_accepts_only_byte_counts(self):
        for stdin, expected_code, expected_total in [
            ('700\n300\n', 0, '1000'),
            ('0\n', 0, '0'),
            ('700\n:: Synchronizing package databases...\n', 1, None),
            ('700\n\n', 1, None),
            ('', 1, None),
        ]:
            with self.subTest(stdin=stdin):
                result = run_bash('sum_download_bytes\n', stdin=stdin)
                self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
                if expected_total is not None:
                    self.assertEqual(result.stdout.splitlines()[0], expected_total)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_probe_and_transfer_failures_are_classified(self):
        probes = [
            ('0 200', 'ok'), ('22 404', 'http 404'), ('0 302', 'http 302'), ('0 503', 'http 503'),
            ('6 000', 'dns'), ('5 000', 'dns'), ('7 000', 'refused'), ('28 000', 'timeout'),
            ('35 000', 'tls'), ('60 000', 'tls'), ('56 000', 'reset'), ('92 000', 'reset'), ('99 000', 'unknown'),
        ]
        transfers = [
            ('124 ""', 'timeout'), ('137 ""', 'timeout'),
            ('1 "Could not resolve host: archive.archlinux.org"', 'dns'),
            ('1 "Resolving timed out after 5000 milliseconds"', 'dns'),
            ('1 "Failed to connect to archive.archlinux.org port 443 after 3 ms: Connection refused"', 'refused'),
            ('1 "The requested URL returned error: 404"', 'http 404'),
            ('1 "OpenSSL SSL_read: Connection reset by peer, errno 104"', 'reset'),
            ('1 "HTTP/2 stream 3 was not closed cleanly: INTERNAL_ERROR (err 2)"', 'reset'),
            ('1 "Error in the HTTP2 framing layer"', 'reset'),
            ('1 "Operation timed out after 30001 milliseconds with 0 bytes received"', 'timeout'),
            ('1 "SSL certificate problem: self-signed certificate"', 'tls'),
            ('1 "error: Partition /tmp too full: 5000 blocks needed, 10 blocks free"', 'storage'),
            ('1 "error: base: signature from \\"Arch\\" is unknown trust"', 'signature'),
            ('1 "error: failed to synchronize all databases (unexpected error)"', 'unknown'),
        ]
        script = ''.join(f'classify_probe_result {args}\n' for args, _ in probes)
        script += ''.join(f'classify_transfer_failure {args}\n' for args, _ in transfers)
        script += ''.join(f'download_failure_retryable {c} && echo "retry {c}" || echo "stop {c}"\n'
                          for c in ['timeout', 'reset', 'dns', 'refused', 'tls', 'http', 'storage', 'signature', 'unknown'])
        result = run_bash(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        expected = [cls for _, cls in probes] + [cls for _, cls in transfers]
        expected += ['retry timeout', 'retry reset'] + [f'stop {c}' for c in ['dns', 'refused', 'tls', 'http', 'storage', 'signature', 'unknown']]
        self.assertEqual(lines[:len(expected)], expected)

    @unittest.skipUnless(sys.platform == 'linux', 'Bash behavior tests run on Linux')
    def test_missing_signature_or_failed_resolution_refuses_preparation(self):
        for resolver in ['printf "base-1-any.pkg.tar.zst\\n"', 'return 1', 'printf "../escape.pkg.tar.zst\\n"']:
            with self.subTest(resolver=resolver), tempfile.TemporaryDirectory() as tmp:
                result = run_bash(r'''
timeout() { printf package > "$STAGE/cache/base-1-any.pkg.tar.zst"; }
pacman() { case " $* " in *'%s'*) printf '%s\n' 1024 ;; *'%f'*) eval "$RESOLVER" ;; esac; }
prepare_install_packages "$STAGE"
''', STAGE=tmp, RESOLVER=resolver)
                self.assertNotEqual(result.returncode, 0)
                final = last_line(result.stderr)
                self.assertTrue(final.startswith('Package preparation failed: '), final)
                self.assertTrue(final.endswith(' The target disk has not been changed.'), final)


if __name__ == '__main__':
    unittest.main()
