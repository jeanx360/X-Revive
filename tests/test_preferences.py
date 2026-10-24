import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("preferences", ROOT / "plataformas/xbox/tools/preferences.py")
prefs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prefs)


class PreferencesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.console = self.root / "console"
        self.run = self.root / "run"
        self.run.mkdir()
        self.console.mkdir()
        self.profile = self.run / "profile"
        self.profile.write_text("fingerprint=abcdef012345\nvulkan=yes\n")
        self.runtime = self.run / "xemu.toml"
        self.runtime.write_text("[sys]\nmem_limit = '128'\n[sys.files]\nhdd_path = '/dev/old'\n"
                                "[display]\nrenderer = 'VULKAN'\n[display.quality]\nsurface_scale = 3\n"
                                "[display.window]\nvsync = false\n")

    def save(self):
        prefs.capture(self.runtime, self.profile, self.run)
        prefs.commit(self.run, self.console)

    def test_reboot_keeps_preferences_and_new_device_paths(self):
        self.save()
        self.runtime.write_text(self.runtime.read_text().replace("'128'", "'64'")
                                .replace("'VULKAN'", "'OPENGL'").replace("/dev/old", "/dev/new")
                                .replace("= 3", "= 1").replace("= false", "= true"))
        prefs.restore(self.runtime, self.profile, self.console)
        data = tomllib.loads(self.runtime.read_text())
        self.assertEqual(data["sys"]["mem_limit"], "128")
        self.assertEqual(data["display"]["renderer"], "VULKAN")
        self.assertEqual(data["display"]["quality"]["surface_scale"], 3)
        self.assertFalse(data["display"]["window"]["vsync"])
        self.assertEqual(data["sys"]["files"]["hdd_path"], "/dev/new")
        self.assertNotIn("hdd_path", next((self.console / "config/xemu").glob("*.json")).read_text())

    def test_vulkan_falls_back_and_different_hardware_uses_defaults(self):
        self.save()
        self.profile.write_text("fingerprint=abcdef012345\nvulkan=no\n")
        self.runtime.write_text("[display]\nrenderer = 'OPENGL'\n")
        prefs.restore(self.runtime, self.profile, self.console)
        self.assertEqual(tomllib.loads(self.runtime.read_text())["display"]["renderer"], "OPENGL")
        self.profile.write_text("fingerprint=000000000000\nvulkan=yes\n")
        self.runtime.write_text("[sys]\nmem_limit = '64'\n")
        prefs.restore(self.runtime, self.profile, self.console)
        self.assertEqual(tomllib.loads(self.runtime.read_text())["sys"]["mem_limit"], "64")

    def test_invalid_runtime_does_not_replace_saved_settings(self):
        self.save()
        target = next((self.console / "config/xemu").glob("*.json"))
        before = target.read_bytes()
        self.runtime.write_text("invalid [ TOML")
        with self.assertRaises(ValueError):
            self.save()
        self.assertEqual(target.read_bytes(), before)

    def test_invalid_saved_settings_do_not_prevent_boot(self):
        self.save()
        target = next((self.console / "config/xemu").glob("*.json"))
        target.write_text("{broken")
        before = self.runtime.read_text()
        result = subprocess.run(["python3", str(ROOT / "plataformas/xbox/tools/preferences.py"),
                                 "restore", str(self.runtime), str(self.profile), str(self.console)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"preferences:", result.stderr)
        self.assertEqual(self.runtime.read_text(), before)

    def test_shutdown_saves_preferences_even_when_eeprom_unchanged(self):
        # Mock only remount: use real save.sh and real capture/commit, with a
        # disposable pendrive directory, never touching a physical disk.
        fw = self.console / "firmware/xbox"
        fw.mkdir(parents=True)
        (fw / "eeprom.bin").write_bytes(b"unchanged")
        (self.run / "eeprom.bin").write_bytes(b"unchanged")
        bindir = self.root / "bin"
        bindir.mkdir()
        mount = bindir / "mount"
        mount.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RUN/mount.log"\n')
        mount.chmod(0o755)
        import os
        env = dict(os.environ, RUN=str(self.run), CONSOLE=str(self.console),
                   PATH=str(bindir) + os.pathsep + os.environ["PATH"])
        subprocess.run(["sh", str(ROOT / "plataformas/xbox/save.sh")], env=env, check=True)
        data = json.loads(next((self.console / "config/xemu").glob("*.json")).read_text())
        self.assertEqual(data["sys.mem_limit"], "128")
        mounts = (self.run / "mount.log").read_text()
        self.assertIn("remount,rw", mounts)
        self.assertIn("remount,ro", mounts)
        self.assertEqual((fw / "eeprom.bin").read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
