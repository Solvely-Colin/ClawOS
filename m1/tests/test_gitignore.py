"""Shared ignore rules must work without a maintainer's private Git excludes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SharedIgnoreRules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': os.devnull}
        # The temporary repository has no private excludes or parent rules.
        for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE',
                     'GIT_COMMON_DIR', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
            self.env.pop(name, None)
        result = self.git('init', '--quiet')
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.repo / '.gitignore').write_bytes((ROOT / '.gitignore').read_bytes())

    def git(self, *args, input=None):
        return subprocess.run(['git', '-c', f'core.excludesFile={os.devnull}',
                               '-C', str(self.repo), *args], input=input,
                              capture_output=True, text=True, env=self.env,
                              check=False)

    def ignored(self, paths):
        result = self.git('check-ignore', '--no-index', '-z', '--stdin',
                          input='\0'.join(paths) + '\0')
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return set(filter(None, result.stdout.split('\0')))

    def test_generated_and_private_paths_are_ignored(self):
        paths = [
            '.claude/worktrees/session/README.md', '.claude/settings.local.json',
            '.codex/worktrees/session/file.py', 'transfer/evidence/report.json',
            'artifacts/m1/out/image.iso', 'checkpoints/disk.qcow2',
            'guest.qcow', 'guest.vhdx', 'guest.vmdk', 'guest.vdi', 'guest.sav',
            'guest.vars', 'guest.fd', 'guest.dpapi', 'bundle.zip', 'build.tar.zst',
            'm1/tests/__pycache__/test.pyc', 'm2/openclaw-plugin/node_modules/x.js',
            'shell-prototype/dist/index.html', 'shell-prototype/test-results/a.json',
            '.venv/bin/python', '.pytest_cache/state', '.ruff_cache/state',
            '.mypy_cache/state', 'pkg.egg-info/PKG-INFO', '.coverage',
            'htmlcov/index.html', 'app.tsbuildinfo', '.idea/workspace.xml',
            '.vscode/settings.json', 'file.swp', '.env', '.env.local',
            '.local/audit.json', 'local-notes/handoff.md', 'docs/local/demo.md',
            'docs/session.local.md', 'docs/history/PLAN.md',
            'docs/history/new-working-note.md',
            'docs/FLIP-DAY.md', 'docs/PUBLIC-SOURCE-READINESS.md',
            'docs/SHARING.md', 'docs/assets/HEADER.md', 'm1/VPS-DEMO.md',
            'm0/STATUS.md', 'm1/STATUS.md', 'm2/STATUS.md', 'm3/STATUS.md',
            'm4/STATUS.md', 'm2/UX-AUDIT.md', 'm2/ACCESSIBILITY-AND-COPILOT.md',
            'm2/ACTIVITY-SHELL.md', 'm2/APPLICATION-SURFACES.md',
            'shell-prototype/design-qa.md',
            'id_ed25519', 'id_rsa', 'client.p12', 'state.sqlite3-wal',
            'state.db', 'state.db-wal', 'state.db-shm', 'auth-profiles.json',
        ]
        self.assertEqual(self.ignored(paths), set(paths))

    def test_source_configs_fixtures_and_assets_stay_visible(self):
        paths = [
            '.env.example', 'm2/openclaw-plugin/.env.example', 'AGENTS.md',
            '.github/workflows/ci.yml', 'm1/config/versions.env',
            'm3/config/clawosd.json', 'm4/tests/fixtures/fake-openclaw',
            'shell-prototype/.openai/hosting.json', 'shell-prototype/package-lock.json',
            'docs/assets/clawos-header.png', 'docs/ARCHITECTURE.md',
            'm1/profile-overlay/airootfs/usr/lib/clawos/clawos-entry',
        ]
        self.assertEqual(self.ignored(paths), set())

    def test_no_tracked_file_is_hidden_by_shared_rules(self):
        result = subprocess.run(['git', '-C', str(ROOT), 'ls-files'],
                                capture_output=True, text=True, check=True)
        self.assertEqual(self.ignored(result.stdout.splitlines()), set(),
                         'Remove generated files from tracking, not from local disk')
