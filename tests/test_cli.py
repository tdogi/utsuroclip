from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.cli import CodexExecutionError, main, safe_title


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

    @staticmethod
    def write_renamed_generated_artifacts(root: Path, title: str = "topic") -> Path:
        generated = root / "output" / "codex-renamed.mp4"
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.touch()
        title_file = root / "work" / "script" / "title.txt"
        title_file.parent.mkdir(parents=True, exist_ok=True)
        title_file.write_text(title, encoding="utf-8")
        return generated

    @staticmethod
    def write_revision_artifacts(root: Path, video_name: str = "20260101000000_topic.mp4") -> Path:
        video = root / "output" / video_name
        video.parent.mkdir(parents=True, exist_ok=True)
        video.touch()
        for directory, filename in (
            (root / "work" / "audio", "scene_001.wav"),
            (root / "work" / "scenes", "scene_001.py"),
            (root / "work" / "rendered", "scene_001.mp4"),
        ):
            directory.mkdir(parents=True, exist_ok=True)
            (directory / filename).touch()
        script = root / "work" / "script" / "script.md"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("script", encoding="utf-8")
        logs = root / "work" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "final-video.txt").write_text(f"output/{video_name}\n", encoding="utf-8")
        (logs / "speaker.txt").write_text("春日部つむぎ\n", encoding="utf-8")
        revise_prompt = root / "prompts" / "revise-video.md"
        revise_prompt.parent.mkdir(parents=True, exist_ok=True)
        revise_prompt.write_text("instructions", encoding="utf-8")
        return video

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
            self.assertEqual(
                (root / "work" / "logs" / "final-video.txt").read_text(encoding="utf-8"),
                f"output/{final_videos[0].name}\n",
            )
            self.assertEqual(
                (root / "work" / "logs" / "speaker.txt").read_text(encoding="utf-8"),
                "春日部つむぎ\n",
            )

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

    def test_generate_recovers_a_video_renamed_by_codex(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            previous_video = root / "output" / "20260101000000_previous.mp4"
            previous_video.parent.mkdir(parents=True, exist_ok=True)
            previous_video.touch()
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = lambda _request: self.write_renamed_generated_artifacts(root)
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 0)
            self.assertTrue(previous_video.is_file())
            self.assertFalse((root / "output" / "codex-renamed.mp4").exists())
            recorded = (root / "work" / "logs" / "final-video.txt").read_text(encoding="utf-8").strip()
            self.assertRegex(recorded, r"^output/\d{14}_topic\.mp4$")
            self.assertTrue((root / recorded).is_file())

    def test_generate_rejects_ambiguous_videos_renamed_by_codex(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)

            def write_multiple_videos(_request: Path) -> None:
                self.write_renamed_generated_artifacts(root)
                (root / "output" / "another.mp4").touch()

            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = write_multiple_videos
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertTrue((root / "output" / "codex-renamed.mp4").is_file())
            self.assertTrue((root / "output" / "another.mp4").is_file())

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

    def test_generate_rejects_a_tool_created_by_codex(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            request = self.make_project(root)
            tools = root / "tools"
            tools.mkdir()
            (tools / "manim_renderer.py").write_text("renderer", encoding="utf-8")

            def create_helper(_request: Path) -> None:
                (tools / "manim_local.py").write_text("helper", encoding="utf-8")
                self.write_generated_artifacts(root)

            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_pipeline.side_effect = create_helper
                result = main(["generate", str(request), "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertTrue((tools / "manim_local.py").is_file())

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

    def test_revise_uses_recorded_video_and_saves_a_distinct_revision(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = self.write_revision_artifacts(root)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_revision.side_effect = lambda _prompt, _target: (
                    root / "output" / "video.mp4"
                ).touch()
                result = main([
                    "revise", "-p", "冒頭の説明をもっと短くして",
                    "--project-root", str(root), "--codex-bin", "fake-codex",
                ])

            self.assertEqual(result, 0)
            runner.return_value.run_revision.assert_called_once_with(
                "冒頭の説明をもっと短くして", target.resolve()
            )
            self.assertEqual(runner.call_args.args[2], "春日部つむぎ")
            revised = list((root / "output").glob("*_revised_*.mp4"))
            self.assertEqual(len(revised), 1)
            self.assertRegex(revised[0].name, r"^20260101000000_topic_revised_\d{14}\.mp4$")
            self.assertTrue(target.is_file())
            self.assertEqual(
                (root / "work" / "logs" / "final-video.txt").read_text(encoding="utf-8"),
                f"output/{revised[0].name}\n",
            )

    def test_revise_recovers_a_video_renamed_by_codex(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = self.write_revision_artifacts(root)
            renamed_video = root / "output" / "codex-revision.mp4"
            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_revision.side_effect = lambda _prompt, _target: renamed_video.touch()
                result = main(["revise", "-p", "棒人間に変更して", "--project-root", str(root)])

            self.assertEqual(result, 0)
            self.assertTrue(target.is_file())
            self.assertFalse(renamed_video.exists())
            revised = list((root / "output").glob("*_revised_*.mp4"))
            self.assertEqual(len(revised), 1)
            self.assertRegex(revised[0].name, r"^20260101000000_topic_revised_\d{14}\.mp4$")
            self.assertEqual(
                (root / "work" / "logs" / "final-video.txt").read_text(encoding="utf-8"),
                f"output/{revised[0].name}\n",
            )

    def test_revise_rejects_a_tool_created_by_codex(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_revision_artifacts(root)
            tools = root / "tools"
            tools.mkdir()
            (tools / "manim_renderer.py").write_text("renderer", encoding="utf-8")

            def create_helper(_prompt: str, _target: Path) -> None:
                (tools / "manim_local.py").write_text("helper", encoding="utf-8")
                (root / "output" / "video.mp4").touch()

            with patch("utsuroclip.cli.CodexRunner") as runner:
                runner.return_value.run_revision.side_effect = create_helper
                result = main(["revise", "-p", "文字を大きくして", "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertTrue((tools / "manim_local.py").is_file())

    def test_revise_restores_the_production_set_after_a_failed_revision(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = self.write_revision_artifacts(root)
            target.write_bytes(b"original video")
            script = root / "work" / "script" / "script.md"
            with patch("utsuroclip.cli.CodexRunner") as runner:
                def fail_after_modifying_artifacts(_prompt: str, _target: Path) -> None:
                    script.write_text("changed script", encoding="utf-8")
                    target.write_bytes(b"changed video")
                    (root / "output" / "video.mp4").write_bytes(b"partial video")
                    (root / "work" / "logs" / "revise-video.stdout.log").write_text(
                        "failure details", encoding="utf-8"
                    )
                    raise CodexExecutionError("Codex failed")

                runner.return_value.run_revision.side_effect = fail_after_modifying_artifacts
                result = main(["revise", "-p", "文字を大きくして", "--project-root", str(root)])

            self.assertEqual(result, 1)
            self.assertEqual(script.read_text(encoding="utf-8"), "script")
            self.assertEqual(target.read_bytes(), b"original video")
            self.assertFalse((root / "output" / "video.mp4").exists())
            self.assertEqual(
                (root / "work" / "logs" / "final-video.txt").read_text(encoding="utf-8"),
                "output/20260101000000_topic.mp4\n",
            )
            self.assertEqual(
                (root / "work" / "logs" / "revise-video.stdout.log").read_text(encoding="utf-8"),
                "failure details",
            )

    def test_revise_rejects_missing_retained_production_assets(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("utsuroclip.cli.CodexRunner") as runner:
                result = main(["revise", "-p", "文字を大きくして", "--project-root", str(root)])

            self.assertEqual(result, 1)
            runner.assert_not_called()

    def test_revise_rejects_a_stale_temporary_video(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_revision_artifacts(root)
            (root / "output" / "video.mp4").touch()
            with patch("utsuroclip.cli.CodexRunner") as runner:
                result = main(["revise", "-p", "文字を大きくして", "--project-root", str(root)])

            self.assertEqual(result, 1)
            runner.assert_not_called()
