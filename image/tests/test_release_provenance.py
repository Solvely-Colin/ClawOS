import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DIGEST = "sha256:70d777aaeb45befc04150df137c4d7c1b5042be442b4c904c38c6f6880bb7844"
ATTEST_ACTION = "actions/attest-build-provenance@0f67c3f4856b2e3261c31976d6725780e5e4c373"


def read(path):
    return (ROOT / path).read_text()


class ReleaseProvenanceTests(unittest.TestCase):
    def test_all_arch_container_entrypoints_share_one_reviewed_digest(self):
        sources = {
            ".github/workflows/ci.yml": read(".github/workflows/ci.yml"),
            ".github/workflows/release.yml": read(".github/workflows/release.yml"),
            "tools/dev/preflight-in-container.sh": read("tools/dev/preflight-in-container.sh"),
        }
        for name, source in sources.items():
            with self.subTest(name=name):
                pins = set(re.findall(r"archlinux:base-devel@(sha256:[0-9a-f]{64})", source))
                self.assertEqual(pins, {DIGEST})
                self.assertIn("2026-09-14", source)
        release = sources[".github/workflows/release.yml"]
        self.assertIn('grep -Fq "@$pinned_digest"', release)
        self.assertIn("Pinned manifest digest:", release)
        self.assertIn("Observed repository digest(s):", release)

    def test_release_attests_and_retains_exact_subjects(self):
        source = read(".github/workflows/release.yml")
        self.assertIn(ATTEST_ACTION, source)
        self.assertRegex(source, r"build:\n(?:.|\n)*?permissions:\n      contents: read\n      id-token: write\n      attestations: write")
        for subject in ("artifacts/m1/out/*.iso", "artifacts/m1/out/SHA256SUMS",
                        "artifacts/m1/out/SBOM.cdx.json"):
            self.assertIn(subject, source)
        self.assertIn("steps.provenance.outputs.bundle-path", source)
        self.assertIn("artifacts/m1/out/ATTESTATION.json", source)

    def test_user_docs_include_repository_bound_verification(self):
        command = "gh attestation verify clawos-*.iso --repo Solvely-Colin/ClawOS"
        self.assertIn(command, read("docs/GETTING-STARTED.md"))
        self.assertIn(command, read("docs/RELEASING.md"))


if __name__ == "__main__":
    unittest.main()
