import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1] / "profile-overlay/airootfs"
MODULE = ROOT / "usr/lib/clawos/clawos_archive_probe.py"
spec = importlib.util.spec_from_file_location("clawos_archive_probe_test", MODULE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ArchiveProbeTests(unittest.TestCase):
    def config(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "versions.env"
        path.write_text(text)
        return path

    def test_snapshot_is_exactly_one_real_date(self):
        valid = self.config("ARCH_SNAPSHOT=2026/08/25\nOPENCLAW_VERSION=test\n")
        self.assertEqual(probe.pinned_snapshot(valid), "2026/08/25")
        for text in ("", "ARCH_SNAPSHOT=latest\n", "ARCH_SNAPSHOT=2026/99/01\n",
                     "ARCH_SNAPSHOT=2026/08/25\nARCH_SNAPSHOT=2026/08/25\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                probe.pinned_snapshot(self.config(text))

    def test_success_heads_only_the_pinned_database_with_bounded_time(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="200", stderr=""))
        result = probe.probe_archive(self.config("ARCH_SNAPSHOT=2026/08/25\n"), runner)
        self.assertTrue(result["reachable"])
        command = runner.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/curl")
        self.assertIn("--head", command)
        self.assertEqual(command[command.index("--max-time") + 1], "10")
        self.assertEqual(command[-1],
                         "https://archive.archlinux.org/repos/2026/08/25/core/os/x86_64/core.db")
        self.assertEqual(runner.call_args.kwargs["timeout"], 12)

    def test_unreachable_results_are_actionable_and_fail_closed(self):
        cases = [
            (SimpleNamespace(returncode=6, stdout="000", stderr=""), "resolved"),
            (SimpleNamespace(returncode=7, stdout="000", stderr=""), "refused"),
            (SimpleNamespace(returncode=28, stdout="000", stderr=""), "10 seconds"),
            (SimpleNamespace(returncode=0, stdout="302", stderr=""), "captive portal"),
            (SimpleNamespace(returncode=0, stdout="404", stderr=""), "HTTP 404"),
        ]
        path = self.config("ARCH_SNAPSHOT=2026/08/25\n")
        for response, message in cases:
            with self.subTest(response=response):
                result = probe.probe_archive(path, Mock(return_value=response))
                self.assertFalse(result["reachable"])
                self.assertIn(message, result["reason"])
        result = probe.probe_archive(path, Mock(side_effect=subprocess.TimeoutExpired("curl", 12)))
        self.assertFalse(result["reachable"])
        self.assertIn("10 seconds", result["reason"])


if __name__ == "__main__":
    unittest.main()
