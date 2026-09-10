"""Positive contracts for the pinned Arch base and ClawOS-owned identity."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('check_arch_base', ROOT / 'image/tests/check_arch_base.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

SERVER = 'https://archive.archlinux.org/repos/2026/08/25/$repo/os/$arch'
IDENTITY = 'NAME="ClawOS"\nID=clawos\nID_LIKE=arch\n'
PACMAN = ('[options]\nSigLevel = Required DatabaseOptional\nCheckSpace\n'
          '[core]\nInclude = /etc/pacman.d/mirrorlist\n'
          '[extra]\nInclude = /etc/pacman.d/mirrorlist\n')


class DistributionBoundary(unittest.TestCase):
    def test_current_source_inputs(self):
        expected = base.check_source(ROOT)
        base.check_root(ROOT / 'image/profile-overlay/airootfs', expected, partial=True)

    def test_valid_archive_and_config(self):
        self.assertEqual(base.archive_server('ARCH_SNAPSHOT=2026/08/25\n'), SERVER)
        base.check_mirror('# snapshot\nServer = ' + SERVER + '\n', SERVER)
        base.check_pacman(PACMAN, SERVER)
        base.check_identity(IDENTITY)
        base.check_packages('# selected packages\nbase\nlinux\n')

    def test_extra_repositories_includes_servers_and_weak_signatures_fail(self):
        bad = [
            PACMAN + '[third-party]\nServer = https://packages.example.invalid\n',
            PACMAN.replace('/etc/pacman.d/mirrorlist', '/etc/pacman.d/custom.conf'),
            PACMAN.replace('Include = /etc/pacman.d/mirrorlist', 'Server = https://example.invalid'),
            PACMAN.replace('Required DatabaseOptional', 'Optional'),
            PACMAN + 'SigLevel = Never\n',
            PACMAN + '[core]\nInclude = /etc/pacman.d/mirrorlist\n',
            PACMAN.replace('SigLevel = Required DatabaseOptional\n', ''),
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    base.check_pacman(text, SERVER)

    def test_mirror_and_snapshot_are_exact(self):
        for text in ('', 'Server = https://example.invalid\n',
                     'Server = ' + SERVER + '\nServer = ' + SERVER + '\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                base.check_mirror(text, SERVER)
        for versions in ('ARCH_SNAPSHOT=latest\n', 'ARCH_SNAPSHOT=2026/99/01\n',
                         'ARCH_SNAPSHOT=2026/08/25\nARCH_SNAPSHOT=2026/08/25\n'):
            with self.subTest(versions=versions), self.assertRaises(ValueError):
                base.archive_server(versions)

    def test_identity_and_package_selection_fail_closed(self):
        for text in ('ID=other\nID_LIKE=arch\n', 'ID=clawos\nID_LIKE=other\n',
                     IDENTITY + 'ID=clawos\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                base.check_identity(text)
        for text in ('', 'base\nbase\n', 'https://example.invalid/pkg.tar.zst\n', 'base --extra\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                base.check_packages(text)

    def make_root(self, root):
        (root / 'etc/pacman.d').mkdir(parents=True)
        (root / 'etc/os-release').write_text(IDENTITY)
        (root / 'etc/pacman.conf').write_text(PACMAN)
        (root / 'etc/pacman.d/mirrorlist').write_text('Server = ' + SERVER + '\n')

    def test_materialized_root_requires_mirror_and_rejects_extra_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            base.check_root(root, SERVER)
            extra = root / 'etc/pacman.d/custom.conf'
            extra.write_text('fixture')
            with self.assertRaises(ValueError):
                base.check_root(root, SERVER)
            extra.unlink()
            (root / 'etc/pacman.d/mirrorlist').unlink()
            with self.assertRaises(ValueError):
                base.check_root(root, SERVER)

    @unittest.skipUnless(sys.platform == 'linux', 'Symlink fixture runs on Linux')
    def test_symlinked_inputs_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            mirror = root / 'etc/pacman.d/mirrorlist'
            mirror.unlink()
            mirror.symlink_to(root / 'absent')
            with self.assertRaises(ValueError):
                base.check_root(root, SERVER)
