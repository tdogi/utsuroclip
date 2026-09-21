from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import tomllib
import unittest


ROOT = Path(__file__).parents[1]


class SetupTests(unittest.TestCase):
    def copy_setup_inputs(self, destination: Path) -> None:
        shutil.copy2(ROOT / "setup.sh", destination / "setup.sh")
        shutil.copy2(ROOT / "AGENTS.dev.md", destination / "AGENTS.dev.md")
        shutil.copy2(ROOT / "AGENTS.user.md", destination / "AGENTS.user.md")
        shutil.copytree(ROOT / ".codex.dev", destination / ".codex.dev")
        shutil.copytree(ROOT / ".codex.user", destination / ".codex.user")
        shutil.copytree(ROOT / ".agents.user", destination / ".agents.user")

    def test_user_mode_deploys_user_settings_and_skill(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.copy_setup_inputs(root)
            result = subprocess.run(["bash", "setup.sh"], cwd=root, text=True, capture_output=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), (root / "AGENTS.user.md").read_text(encoding="utf-8"))
            config_path = root / ".codex" / "config.toml"
            self.assertTrue(config_path.is_file())
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
            self.assertTrue(config["sandbox_workspace_write"]["network_access"])
            self.assertTrue(config["features"]["network_proxy"]["enabled"])
            self.assertEqual(config["features"]["network_proxy"]["domains"], {"127.0.0.1": "allow"})
            self.assertTrue((root / ".agents" / "skills" / "video-generation" / "SKILL.md").is_file())

    def test_development_mode_deploys_development_settings(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.copy_setup_inputs(root)
            result = subprocess.run(["bash", "setup.sh", "--dev"], cwd=root, text=True, capture_output=True)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), (root / "AGENTS.dev.md").read_text(encoding="utf-8"))
            self.assertTrue((root / ".codex" / "config.toml").is_file())
