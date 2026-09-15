import json
from pathlib import Path
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
generate = runpy.run_path(str(ROOT / "image/bin/generate-openclaw-inventory"))["generate"]


class OpenClawInventoryTests(unittest.TestCase):
    def package(self, path, name, version, license_value="MIT", dependencies=None):
        path.mkdir(parents=True)
        payload = {"name": name, "version": version, "license": license_value}
        if dependencies:
            payload["dependencies"] = dependencies
        (path / "package.json").write_text(json.dumps(payload))

    def test_manifest_lock_and_license_texts_follow_installed_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "openclaw"
            self.package(root, "openclaw", "1.2.3", dependencies={"alpha": "^2"})
            (root / "LICENSE").write_text("root license")
            alpha = root / "node_modules/alpha"
            self.package(alpha, "alpha", "2.1.0", "Apache-2.0")
            (alpha / "COPYING.txt").write_text("alpha license")
            nested = alpha / "node_modules/@scope/nested"
            self.package(nested, "@scope/nested", "3.0.0", {"type": "BSD-2-Clause"})
            output, lock = Path(temporary) / "inventory", Path(temporary) / "work/package-lock.json"
            result = generate(root, output, lock)
            self.assertEqual(result["packageCount"], 3)
            self.assertEqual([item["name"] for item in result["packages"]],
                             ["@scope/nested", "alpha", "openclaw"])
            self.assertEqual(result["packages"][0]["license"], "BSD-2-Clause")
            self.assertEqual(result["packages"][1]["path"],
                             "/usr/lib/node_modules/openclaw/node_modules/alpha")
            self.assertEqual((output / "license-texts/_root/LICENSE").read_text(), "root license")
            self.assertEqual((output / "license-texts/node_modules/alpha/COPYING.txt").read_text(),
                             "alpha license")
            package_lock = json.loads(lock.read_text())
            self.assertEqual(package_lock["lockfileVersion"], 3)
            self.assertIn("node_modules/openclaw/node_modules/alpha/node_modules/@scope/nested",
                          package_lock["packages"])

    def test_refuses_to_overwrite_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "openclaw"
            self.package(root, "openclaw", "1.0.0")
            output = Path(temporary) / "inventory"
            output.mkdir()
            (output / "existing").write_text("keep")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                generate(root, output, Path(temporary) / "lock.json")

    def test_build_validation_installer_and_release_consume_inventory(self):
        build = (ROOT / "image/bin/build-iso").read_text()
        self.assertIn("generate-openclaw-inventory", build)
        self.assertIn("npm sbom --package-lock-only --sbom-format cyclonedx --omit dev", build)
        self.assertIn("npm audit --json --package-lock-only --omit dev", build)
        for name in ("SBOM.cdx.json", "AUDIT.json", "AUDIT-STATUS.txt",
                     "OPENCLAW-LICENSES.json"):
            self.assertIn(name, build)
            self.assertIn(name, (ROOT / ".github/workflows/release.yml").read_text())
        installer = (ROOT / "image/profile-overlay/airootfs/usr/local/bin/clawos-install-dev").read_text()
        self.assertIn("cp -a /usr/share/licenses/openclaw-npm/.", installer)
        validation = (ROOT / "image/tests/validate-iso.sh").read_text()
        self.assertIn("usr/share/licenses/openclaw-npm", validation)
        release = (ROOT / "tools/ci/build-release.sh").read_text()
        self.assertIn("sha256sum -c SHA256SUMS", release)


if __name__ == "__main__":
    unittest.main()
