"""OpenClaw version-pin consistency.

image/config/versions.env is the single lock for the OpenClaw runtime that
build-iso ships, the installer verifies, clawosd promotes and the delivery
adapter guards. Every other file that hard-codes that version must agree with
the lock, so a bump cannot silently leave one consumer behind. This test
reads files only: no shell, no subprocess, Windows and Linux alike.
"""
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

VERSIONS_ENV = ROOT / "image/config/versions.env"
CLAWOSD_CONFIG = ROOT / "services/clawosd/config/clawosd.json"
DELIVERY_ADAPTER = ROOT / "integrations/openclaw/lib/deployment-delivery.js"
PLUGIN_MANIFEST = ROOT / "integrations/openclaw/package.json"

# Files that restate the pin in prose or fixtures. Each must contain the
# pinned version at least once unless `must_mention` is False. `allow_older`
# permits deliberate older literals (a compatibility floor, an "update
# available" fixture); a literal newer than the lock is never acceptable.
MENTIONS = {
    "CONTRIBUTING.md": dict(must_mention=True, allow_older=False),
    "docs/SELF-DEVELOPMENT.md": dict(must_mention=True, allow_older=False),
    "services/clawosd/tests/test_clawosd.py": dict(must_mention=True, allow_older=False),
    "integrations/openclaw/test/panel.test.js": dict(must_mention=True, allow_older=True),
    "integrations/openclaw/package.json": dict(must_mention=False, allow_older=True),
}

# OpenClaw uses unpadded CalVer (2026.8.2). Zero-padded dates such as the
# 2026.09.06 in an ISO file name therefore do not match. The optional
# backslash accepts the escaped form used inside JavaScript regex literals.
CALVER = re.compile(r"(?<![\w.])(20\d{2})\\?\.([1-9]|1[0-2])\\?\.(\d{1,3})(?![\w.\\])")
GUARD = re.compile(r"pkg\.version !== '([^']+)'")
FLOOR = re.compile(r"^>=\s*(\S+)$")


def as_tuple(version):
    return tuple(int(part) for part in version.split("."))


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def load_lock():
    values = {}
    for line in VERSIONS_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def literals(text):
    return sorted({".".join(match.groups()) for match in CALVER.finditer(text)})


class OpenClawVersionPin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load_lock()
        cls.pin = cls.lock.get("OPENCLAW_VERSION", "")

    def test_lock_defines_an_unpadded_calver_version(self):
        self.assertIn("OPENCLAW_VERSION", self.lock, f"{VERSIONS_ENV} lacks OPENCLAW_VERSION")
        self.assertRegex(self.pin, r"^20\d{2}\.([1-9]|1[0-2])\.\d{1,3}$")
        self.assertEqual(literals(self.pin), [self.pin])

    def test_clawosd_promotes_the_locked_version(self):
        config = json.loads(CLAWOSD_CONFIG.read_text(encoding="utf-8"))
        promoted = config.get("openclaw", {}).get("promotedVersion")
        self.assertEqual(config['openclaw']['promotedCommit'], self.lock['OPENCLAW_COMMIT'])
        self.assertEqual(config['openclaw']['promotedIntegrity'], self.lock['OPENCLAW_INTEGRITY'])
        self.assertEqual(
            promoted, self.pin,
            f"{CLAWOSD_CONFIG} openclaw.promotedVersion={promoted!r} but "
            f"{VERSIONS_ENV} pins OPENCLAW_VERSION={self.pin!r}",
        )

    def test_build_input_integrity_and_commit_are_pinned_and_consumed(self):
        self.assertRegex(self.lock.get('OPENCLAW_INTEGRITY', ''), r'^sha512-[A-Za-z0-9+/]{86}==$')
        self.assertRegex(self.lock.get('OPENCLAW_COMMIT', ''), r'^[0-9a-f]{7,40}$')
        build = read('image/bin/build-iso')
        self.assertIn('"$OPENCLAW_INTEGRITY"', build)
        self.assertIn('"$OPENCLAW_COMMIT"', build)
        self.assertIn('"$OPENCLAW_COMMIT"', read('image/tests/validate-iso.sh'))

    def test_delivery_adapter_guards_the_locked_version(self):
        source = DELIVERY_ADAPTER.read_text(encoding="utf-8")
        guards = GUARD.findall(source)
        self.assertEqual(len(guards), 1, f"{DELIVERY_ADAPTER} must contain exactly one pkg.version guard")
        self.assertEqual(
            guards[0], self.pin,
            f"{DELIVERY_ADAPTER} guards {guards[0]!r} but {VERSIONS_ENV} pins {self.pin!r}; "
            "an OpenClaw bump must update and reverify the adapter",
        )
        self.assertEqual(literals(source), [self.pin], "stale version literal in the delivery adapter")

    def test_release_metadata_includes_the_integrity_lock(self):
        source = read('tools/ci/build-release.sh')
        metadata = source.split('} >"$out/BUILD-METADATA.txt"', 1)[0]
        self.assertIn('cat image/config/versions.env', metadata)
        self.assertIn('OPENCLAW_INTEGRITY', self.lock)

    def test_plugin_compatibility_floors_admit_the_locked_version(self):
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        compat = manifest.get("openclaw", {}).get("compat", {})
        floors = {
            "peerDependencies.openclaw": manifest.get("peerDependencies", {}).get("openclaw", ""),
            "openclaw.compat.pluginApi": compat.get("pluginApi", ""),
            "openclaw.compat.minGatewayVersion": ">=" + compat.get("minGatewayVersion", ""),
        }
        for name, spec in floors.items():
            with self.subTest(field=name):
                match = FLOOR.match(spec)
                self.assertIsNotNone(match, f"{PLUGIN_MANIFEST} {name}={spec!r} is not a >= floor")
                self.assertLessEqual(
                    as_tuple(match.group(1)), as_tuple(self.pin),
                    f"{PLUGIN_MANIFEST} {name}={spec!r} excludes the pinned OpenClaw {self.pin}",
                )

    def test_documents_and_fixtures_agree_with_the_lock(self):
        pinned = as_tuple(self.pin)
        for relative, rule in MENTIONS.items():
            with self.subTest(file=relative):
                found = literals(read(relative))
                if rule["must_mention"]:
                    self.assertIn(self.pin, found, f"{relative} no longer states the pinned OpenClaw {self.pin}")
                newer = [version for version in found if as_tuple(version) > pinned]
                self.assertEqual(newer, [], f"{relative} names OpenClaw versions newer than the lock {self.pin}")
                if not rule["allow_older"]:
                    older = [version for version in found if as_tuple(version) < pinned]
                    self.assertEqual(older, [], f"{relative} still names a superseded OpenClaw version")


if __name__ == "__main__":
    unittest.main()
