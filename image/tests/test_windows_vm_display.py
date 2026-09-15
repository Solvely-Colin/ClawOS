from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class WindowsVMDisplayTests(unittest.TestCase):
    def test_builder_uses_scaled_ungrabbed_gtk_with_absolute_pointer(self):
        source = (ROOT / "tools/windows/run-clawos-builder.ps1").read_text()
        display = ('gtk,zoom-to-fit=on,keep-aspect-ratio=on,full-screen=off,show-menubar=off,'
                   'grab-on-hover=off,show-cursor=on,window-close=off')
        self.assertIn(f'-display "{display}"', source)
        self.assertNotIn('-display "sdl', source)
        self.assertIn('-device "usb-tablet,id=clawos-pointer"', source)
        self.assertIn('[ClawOSPrimaryDisplay]::GetSystemMetrics(0)', source)
        self.assertIn('[ClawOSPrimaryDisplay]::GetSystemMetrics(1)', source)
        self.assertIn('Unsupported primary display geometry', source)
        self.assertIn('-device "virtio-vga,xres=$displayWidth,yres=$displayHeight"', source)
        self.assertNotIn('virtio-vga,xres=1440,yres=900', source)
        self.assertIn('clawos-v01-build.qcow2', source)
        self.assertIn('serial=CLAWOS-V01-BUILD', source)
        self.assertIn('-qmp "tcp:127.0.0.1:4444,server=on,wait=off"', source)


if __name__ == "__main__":
    unittest.main()
