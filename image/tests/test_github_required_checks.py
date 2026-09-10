"""Offline coverage of the future ruleset payload and its readback expectation."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECTED = {"unit-tests", "arch-preflight", "container-wrapper", "prototype"}


class RequiredChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "tools/github/enable-protections.sh").read_text()

    def test_expected_checks_match_ci_jobs(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text().split("\njobs:\n", 1)[1]
        self.assertEqual(set(re.findall(r"^  ([a-z][a-z0-9-]*):$", workflow, re.M)), EXPECTED)

    def test_generated_payload_for_each_merge_method(self):
        bash = os.environ.get("CLAWOS_TEST_BASH") or shutil.which("bash")
        self.assertIsNotNone(bash, "Bash is required to validate the ruleset renderer")
        # Extract only the JSON renderer; never invoke the script's API/main code.
        function = re.search(r"^ruleset_main_body\(\) \{.*?(?=^ruleset_tags_body\(\))",
                             self.script, re.M | re.S).group()
        for method in ("merge", "squash", "rebase"):
            with self.subTest(method=method):
                output = subprocess.check_output(
                    [bash, "--noprofile", "--norc", "-c",
                     f"MERGE_METHOD={method}\n{function}\nruleset_main_body"],
                    text=True, timeout=10)
                body = json.loads(output)
                rule = next(r for r in body["rules"] if r["type"] == "required_status_checks")
                names = [c["context"] for c in rule["parameters"]["required_status_checks"]]
                self.assertEqual(set(names), EXPECTED)
                self.assertEqual(len(names), len(EXPECTED), "No duplicate checks")
                self.assertEqual(body["conditions"]["ref_name"]["include"], ["refs/heads/main"])

    def test_readback_requires_the_same_complete_set(self):
        line = next(line for line in self.script.splitlines()
                    if 'check "ruleset \'main\' required checks"' in line)
        expected_csv = line.rsplit('"', 2)[1]
        self.assertEqual(expected_csv, ",".join(sorted(EXPECTED)))


if __name__ == "__main__":
    unittest.main()
