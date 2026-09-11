import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import subprocess
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1] / 'profile-overlay/airootfs'
MODULE = ROOT / 'usr/lib/clawos/clawos_install_targets.py'
spec = importlib.util.spec_from_file_location('environment_targets', MODULE)
targets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(targets)


class InstallEnvironmentTests(unittest.TestCase):
    def test_detector_success_reports_vm_type_and_uses_bounded_absolute_command(self):
        for name in ('kvm', 'qemu', 'microsoft', 'vmware'):
            with self.subTest(name=name), patch.object(targets.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=name + '\n')) as run:
                self.assertEqual(targets.virtualization(), {'kind': 'vm', 'type': name})
                self.assertEqual(run.call_args.args[0], ['/usr/bin/systemd-detect-virt', '--vm'])
                self.assertEqual(run.call_args.kwargs['timeout'], 3)

    def test_only_detector_none_exit_one_identifies_physical_machine(self):
        with patch.object(targets.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout='none\n')):
            self.assertEqual(targets.virtualization(), {'kind': 'physical', 'type': 'none'})

    def test_detector_errors_and_malformed_results_are_unknown(self):
        for code, output in ((0, ''), (0, 'none'), (1, 'kvm'), (2, 'none'), (0, 'kvm\nextra')):
            with self.subTest(code=code, output=output), patch.object(targets.subprocess, 'run', return_value=SimpleNamespace(returncode=code, stdout=output)):
                self.assertEqual(targets.virtualization(), {'kind': 'unknown', 'type': None})
        for error in (OSError('missing'), subprocess.TimeoutExpired('detector', 3)):
            with patch.object(targets.subprocess, 'run', side_effect=error):
                self.assertEqual(targets.virtualization()['kind'], 'unknown')

    def test_unknown_is_refused_even_with_hardware_opt_in(self):
        with patch.object(targets, 'virtualization', return_value={'kind': 'unknown', 'type': None}):
            for override in (False, True):
                with self.assertRaisesRegex(ValueError, 'Cannot verify virtualization'):
                    targets.require_install_environment(override)

    def test_physical_discovery_is_blocked_before_disk_queries(self):
        with patch.object(targets, 'virtualization', return_value={'kind': 'physical', 'type': 'none'}), patch.object(targets, 'inventory') as inventory:
            with self.assertRaisesRegex(ValueError, 'VM-only'):
                targets.list_targets()
            inventory.assert_not_called()

    def test_gui_callback_refuses_non_vm_without_running_installer(self):
        source = (ROOT / 'usr/lib/clawos/clawos-live-welcome').read_text()
        method = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == 'start_install')
        code = compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<start_install>', 'exec')
        for kind in ('physical', 'unknown'):
            namespace = {'virtualization': lambda: {'kind': kind}}
            exec(code, namespace)
            view = SimpleNamespace(installing=False, error=Mock(), install_button=Mock())
            namespace['start_install'](view)
            view.install_button.set_sensitive.assert_called_once_with(False)
            self.assertIn('VM-only', view.error.set_text.call_args.args[0])
            self.assertFalse(view.installing)
        self.assertNotIn('--experimental-hardware', source)

    def test_shell_passes_override_to_every_recheck_before_download_and_erase(self):
        source = (ROOT / 'usr/local/bin/clawos-install-dev').read_text()
        self.assertIn('--experimental-hardware) environment_args+=(--experimental-hardware)', source)
        self.assertIn('"${environment_args[@]}"', source)
        guard = source.index('plan=$(recheck validate --confirm "$confirmation")')
        self.assertLess(guard, source.index('prepare_install_packages "$download_root"'))
        self.assertLess(guard, source.index('sfdisk --wipe always'))


if __name__ == '__main__':
    unittest.main()
