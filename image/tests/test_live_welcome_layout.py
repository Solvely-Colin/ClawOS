"""Pin GTK containment; real pixel/allocation proof still requires the VM."""
import ast
import pathlib
import unittest


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


if __name__ == "__main__":
    unittest.main()
