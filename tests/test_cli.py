from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.cli import main


class CliTests(unittest.TestCase):
    def make_project(self, directory: Path) -> Path:
        for name in ("research.md", "write-script.md", "generate-video.md"):
            path = directory / "prompts" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("instructions", encoding="utf-8")
        request = directory / "input" / "request.md"
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text("# topic", encoding="utf-8")
        return request

    def test_generate_prepares_workspace_and_runs_runner(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: (root / "output" / "video.mp4").touch()
                result = main([
                    "generate", str(request), "--project-root", str(root), "--codex-bin", "fake-codex"
                ])

            self.assertEqual(result, 0)
            runner.assert_called_once()
            runner.return_value.run_pipeline.assert_called_once_with(request.resolve())
            self.assertEqual(runner.call_args.args[2], "春日部つむぎ")
            self.assertTrue((root / "work" / "logs").is_dir())
            self.assertTrue((root / "output").is_dir())

    def test_generate_passes_selected_speaker_to_runner(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: (root / "output" / "video.mp4").touch()
                result = main([
                    "generate", str(request), "--project-root", str(root), "--speaker", "ずんだもん"
                ])

            self.assertEqual(result, 0)
            self.assertEqual(runner.call_args.args[2], "ずんだもん")

    def test_generate_requires_final_video(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner"):
                result = main(["generate", str(request), "--project-root", str(root)])
        self.assertEqual(result, 1)

    def test_generate_rejects_missing_request(self) -> None:
        with TemporaryDirectory() as temp:
            result = main(["generate", "missing.md", "--project-root", temp])
        self.assertEqual(result, 2)

    def test_generate_requires_project_prompts(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.md"
            request.write_text("# topic", encoding="utf-8")
            result = main(["generate", str(request), "--project-root", str(root)])
        self.assertEqual(result, 1)
