import base64
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
verify = runpy.run_path(str(ROOT / 'image/bin/verify-openclaw-archive'))['verify']
COMMIT = '0965053fe6b9341776df147a6934b7485c60b5ca'


class OpenClawArchiveTests(unittest.TestCase):
    def archive(self, version='2026.8.2', commit=COMMIT, duplicate=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'runtime.tgz'
        with tarfile.open(path, 'w:gz') as archive:
            entries = [('package/package.json', {'name': 'openclaw', 'version': version}),
                       ('package/dist/build-info.json', {'version': version, 'commit': commit})]
            if duplicate:
                entries.append(entries[0])
            for name, data in entries:
                raw = json.dumps(data).encode()
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode()
        return path, integrity

    def test_verified_archive_matches_version_and_commit(self):
        path, pin = self.archive()
        self.assertEqual(verify(path, pin, '2026.8.2', '0965053'), COMMIT)

    def test_tamper_is_refused_before_archive_parsing(self):
        path, pin = self.archive()
        path.write_bytes(b'not even a tarball')
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            verify(path, pin, '2026.8.2', '0965053')

    def test_wrong_version_or_commit_and_duplicate_metadata_are_refused(self):
        for options, reason in (({'version': '2026.8.1'}, 'version'),
                                ({'commit': 'a' * 40}, 'commit'),
                                ({'duplicate': True}, 'duplicate')):
            with self.subTest(options=options):
                path, pin = self.archive(**options)
                with self.assertRaisesRegex(ValueError, reason):
                    verify(path, pin, '2026.8.2', '0965053')

    def test_invalid_pins_are_refused(self):
        path, pin = self.archive()
        for invalid in ('', pin + ' extra', pin.replace('sha512-', 'sha256-')):
            with self.assertRaisesRegex(ValueError, 'integrity pin'):
                verify(path, invalid, '2026.8.2', '0965053')

    def test_build_verifies_before_install_and_disables_pack_scripts(self):
        source = (ROOT / 'image/bin/build-iso').read_text()
        self.assertIn('--ignore-scripts --json', source)
        self.assertLess(source.index('image/bin/verify-openclaw-archive'), source.index('npm install --global'))
        self.assertIn('"$runtime_archive"; then', source)
        self.assertIn('--allow-scripts="file:$runtime_archive,', source)


if __name__ == '__main__':
    unittest.main()
