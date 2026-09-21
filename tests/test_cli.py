from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.cli import main, safe_title


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

    @staticmethod
    def write_generated_artifacts(root: Path, title: str = "topic") -> None:
        (root / "output" / "video.mp4").touch()
        title_file = root / "work" / "script" / "title.txt"
        title_file.parent.mkdir(parents=True, exist_ok=True)
        title_file.write_text(title, encoding="utf-8")

    def test_generate_prepares_workspace_and_runs_runner(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main([
                    "generate", str(request), "--project-root", str(root), "--codex-bin", "fake-codex"
                ])

            self.assertEqual(result, 0)
            runner.assert_called_once()
            runner.return_value.run_pipeline.assert_called_once_with(request.resolve())
            self.assertEqual(runner.call_args.args[2], "春日部つむぎ")
            self.assertTrue((root / "work" / "logs").is_dir())
            self.assertTrue((root / "output").is_dir())
            final_videos = list((root / "output").glob("*.mp4"))
            self.assertEqual(len(final_videos), 1)
            self.assertRegex(final_videos[0].name, r"^\d{14}_topic\.mp4$")

    def test_generate_passes_selected_speaker_to_runner(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main([
                    "generate", str(request), "--project-root", str(root), "--speaker", "ずんだもん"
                ])

            self.assertEqual(result, 0)
            self.assertEqual(runner.call_args.args[2], "ずんだもん")

    def test_generate_requires_confirmation_before_cleaning_artifacts(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            artifact = root / "work" / "audio" / "scene_001.wav"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.touch()
            with patch("builtins.input", return_value="n"), patch("utsuroclip.cli.CodexRunner") as runner:
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertTrue(artifact.is_file())
            runner.assert_not_called()

    def test_generate_cleans_artifacts_after_confirmation(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            artifact = root / "work" / "audio" / "scene_001.wav"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.touch()
            with patch("builtins.input", return_value="y"), patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 0)
            self.assertFalse(artifact.exists())
            runner.assert_called_once()

    def test_generate_yes_cleans_artifacts_without_confirmation(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            artifact = root / "work" / "audio" / "scene_001.wav"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.touch()
            with patch("builtins.input") as input_, patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main(["generate", str(request), "--project-root", str(root), "-y"])

            self.assertEqual(result, 0)
            self.assertFalse(artifact.exists())
            input_.assert_not_called()

    def test_generate_keeps_existing_completed_videos(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            previous_video = root / "output" / "20260101000000_previous.mp4"
            previous_video.parent.mkdir(parents=True, exist_ok=True)
            previous_video.write_bytes(b"previous")
            artifact = root / "work" / "audio" / "scene_001.wav"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.touch()
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main(["generate", str(request), "--project-root", str(root), "--yes"])

            self.assertEqual(result, 0)
            self.assertEqual(previous_video.read_bytes(), b"previous")

    def test_generate_does_not_overwrite_same_named_completed_video(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            previous_video = root / "output" / "20260101000000_topic.mp4"
            previous_video.parent.mkdir(parents=True, exist_ok=True)
            previous_video.write_bytes(b"previous")
            with patch("utsuroclip.cli.datetime") as current_time, patch("utsuroclip.cli.CodexRunner") as runner:
                current_time.now.return_value = datetime(2026, 1, 1)
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_generated_artifacts(root)
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertEqual(previous_video.read_bytes(), b"previous")
            self.assertTrue((root / "output" / "video.mp4").is_file())

    def test_generate_rejects_missing_title(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: (root / "output" / "video.mp4").touch()
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 1)

    def test_safe_title_replaces_unsafe_filename_characters(self) -> None:
        self.assertEqual(safe_title(" 空/青:なぜ？ "), "空_青_なぜ")

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
