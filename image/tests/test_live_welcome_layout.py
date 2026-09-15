"""Pin GTK containment; real pixel/allocation proof still requires the VM."""
import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "profile-overlay/airootfs/usr/lib/clawos/clawos-live-welcome"


class LiveWelcomeLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text())
        cls.install = next(node for node in ast.walk(tree)
                           if isinstance(node, ast.FunctionDef) and node.name == "show_install")
        cls.calls = {ast.unparse(node) for node in ast.walk(cls.install)
                     if isinstance(node, ast.Call)}

    def test_options_scroll_without_propagating_natural_height(self):
        self.assertIn("Gtk.ScrolledWindow()", self.calls)
        self.assertIn("options.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)", self.calls)
        self.assertIn("options.set_propagate_natural_height(False)", self.calls)
        self.assertIn("options.add(panes)", self.calls)
        self.assertIn("content.pack_start(options, True, True, 0)", self.calls)

    def test_actions_are_outside_scrollable_options(self):
        self.assertIn("content.pack_end(actions, False, False, 0)", self.calls)
        self.assertIn("actions.pack_start(self.install_button, True, True, 0)", self.calls)
        self.assertFalse(any(call.startswith("right.pack_end(self.install_button") for call in self.calls))
        self.assertIn("actions.pack_start(back_slot, True, True, 0)", self.calls)

    def test_erase_starts_disabled(self):
        self.assertIn("self.install_button.set_sensitive(False)", self.calls)

    def test_archive_probe_is_async_and_gates_erase(self):
        source = SOURCE.read_text()
        self.assertIn("from clawos_archive_probe import probe_archive", source)
        self.assertIn("threading.Thread(target=self._probe_archive_worker, daemon=True).start()", source)
        self.assertIn('"Package archive", "row-label"', source)
        self.assertIn('state, style = "Reachable", "mono-success"', source)
        self.assertIn('state, style = "Unreachable", "danger"', source)
        self.assertIn('context.add_class(box_style)', source)
        self.assertIn('self.archive_event_label = message_label', source)
        self.assertIn('"Pinned package archive unreachable")', source)
        self.assertIn("archive_ok = self.archive_result.get('reachable')", source)
        self.assertIn("environment_ok and archive_ok and confirmed", source)
        self.assertIn("Package archive unreachable:", source)
        self.assertNotIn("def _network_ready", source)
        self.assertNotIn('"ip", "-json", "route"', source)

    def test_unreachable_archive_disables_erase_and_blocks_launch(self):
        source = SOURCE.read_text()
        tree = ast.parse(source)
        methods = {node.name: node for node in ast.walk(tree)
                   if isinstance(node, ast.FunctionDef)}

        validate_code = compile(ast.fix_missing_locations(
            ast.Module(body=[methods['_validate_passphrase']], type_ignores=[])),
            '<validate-passphrase>', 'exec')
        validate_namespace = {'confirmation_token': lambda target: f'ERASE-{target}'}
        exec(validate_code, validate_namespace)
        view = SimpleNamespace(
            _passphrase_problem=Mock(return_value=''), target='/dev/vda',
            erase_confirmation=Mock(), install_environment={'kind': 'vm'},
            archive_result={'reachable': False, 'checking': False,
                            'reason': 'DNS is unavailable.'},
            archive_install_status=Mock(), install_button=Mock(), error=Mock(), installing=False,
        )
        view.erase_confirmation.get_text.return_value = 'ERASE-/dev/vda'
        validate_namespace['_validate_passphrase'](view)
        view.install_button.set_sensitive.assert_called_once_with(False)
        view.error.set_text.assert_called_once_with('')

        start_code = compile(ast.fix_missing_locations(
            ast.Module(body=[methods['start_install']], type_ignores=[])),
            '<start-install>', 'exec')
        start_namespace = {'virtualization': lambda: {'kind': 'vm'}}
        exec(start_code, start_namespace)
        view._start_archive_probe = Mock()
        start_namespace['start_install'](view)
        view._start_archive_probe.assert_called_once_with()
        self.assertFalse(view.installing)


if __name__ == "__main__":
    unittest.main()
