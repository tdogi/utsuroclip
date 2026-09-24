from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.codex import CodexExecutionError, CodexRunner, StageSummary, TokenUsage
from utsuroclip.project import ProjectPaths


class FakeCodexProcess:
    def __init__(self, events: list[dict[str, object]], stderr: str = "", returncode: int = 0) -> None:
        self.stdout = StringIO("".join(json.dumps(event) + "\n" for event in events))
        self.stderr = StringIO(stderr)
        self.returncode = returncode

    def wait(self) -> int:
        return self.returncode


class CodexRunnerTests(unittest.TestCase):
    def make_project(self, directory: Path) -> tuple[ProjectPaths, Path]:
        project = ProjectPaths(directory)
        for name in ("research.md", "write-script.md", "generate-video.md", "self-check-video.md"):
            path = project.prompts / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name}", encoding="utf-8")
        request = directory / "input" / "request.md"
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text("# topic", encoding="utf-8")
        project.prepare_workspace()
        return project, request

    def test_runs_all_stages_with_workspace_write_and_logs_output(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            events = [
                {"type": "thread.started"},
                {
                    "type": "item.started",
                    "item": {"type": "command_execution", "command": "manim scene.py"},
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 20,
                        "output_tokens": 30,
                        "reasoning_output_tokens": 40,
                    },
                },
            ]
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen",
                side_effect=[FakeCodexProcess(events, "progress\n") for _ in range(4)],
            ) as popen, redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()) as stderr:
                CodexRunner(project, "fake-codex").run_pipeline(request)

            self.assertEqual(popen.call_count, 4)
            first_command = popen.call_args_list[0].args[0]
            self.assertEqual(first_command[:4], ["fake-codex", "exec", "--sandbox", "workspace-write"])
            self.assertIn("--json", first_command)
            self.assertIn("--output-last-message", first_command)
            video_command = popen.call_args_list[2].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", video_command)
            self.assertIn("features.network_proxy.enabled=true", video_command)
            self.assertIn('features.network_proxy.domains={ "127.0.0.1" = "allow" }', video_command)
            check_command = popen.call_args_list[3].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", check_command)
            self.assertIn("現在の工程: self-check-video", check_command[-1])
            self.assertTrue((project.logs / "self-check-video.stdout.log").is_file())
            self.assertTrue((project.logs / "research.stdout.log").is_file())
            self.assertIn('"turn.completed"', (project.logs / "research.stdout.log").read_text(encoding="utf-8"))
            self.assertEqual((project.logs / "research.stderr.log").read_text(encoding="utf-8"), "progress\n")
            self.assertIn("[research] 実行: manim scene.py", stdout.getvalue())
            self.assertIn("input 400", stdout.getvalue())
            self.assertIn("[research] progress", stderr.getvalue())

    def test_includes_selected_speaker_in_video_generation_prompt(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            prompt = CodexRunner(project, speaker="四国めたん")._build_prompt(
                "generate-video", project.prompts / "generate-video.md", request
            )

        self.assertIn("ナレーション話者: 四国めたん", prompt)
        self.assertIn("--speaker", prompt)

    def test_commercial_mode_reaches_video_stages_only(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            runner = CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"})
            (project.work / "scenes" / "scene_001.py").write_text('Text("A")', encoding="utf-8")
            video_prompt = runner._build_prompt(
                "generate-video", project.prompts / "generate-video.md", request
            )
            research_prompt = runner._build_prompt(
                "research", project.prompts / "research.md", request
            )
            self.assertIn("商用利用モード: 有効", video_prompt)
            self.assertIn("Noto Sans Math", video_prompt)
            self.assertNotIn("商用利用モード", research_prompt)
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen",
                side_effect=[FakeCodexProcess([]) for _ in range(4)],
            ) as popen, redirect_stdout(StringIO()):
                runner.run_pipeline(request)
            self.assertNotIn("env", popen.call_args_list[0].kwargs)
            self.assertEqual(popen.call_args_list[2].kwargs["env"]["FONTCONFIG_FILE"], "/tmp/fonts.conf")
            self.assertEqual(popen.call_args_list[3].kwargs["env"]["FONTCONFIG_FILE"], "/tmp/fonts.conf")

    def test_commercial_mode_repairs_disallowed_font_before_self_check(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            scene = project.work / "scenes" / "scene_001.py"
            rendered = project.work / "rendered" / "scene_001.mp4"
            stages = []

            def run_stage(stage, *_args, **_kwargs):
                stages.append(stage)
                if stage == "generate-video":
                    scene.write_text('Text("A", font="DejaVu Sans")', encoding="utf-8")
                if stage == "repair-commercial-fonts-1":
                    scene.write_text('Text("A", font="Noto Sans CJK JP")', encoding="utf-8")
                    rendered.write_bytes(b"rerendered")
                return StageSummary(stage, 0, TokenUsage())

            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch.object(
                CodexRunner, "_run_stage", side_effect=run_stage
            ), redirect_stdout(StringIO()):
                CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"}).run_pipeline(request)

            self.assertEqual(stages, [
                "research", "write-script", "generate-video", "repair-commercial-fonts-1",
                "self-check-video",
            ])

    def test_commercial_mode_rechecks_after_self_check_and_limits_repairs(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            scene = project.work / "scenes" / "scene_001.py"
            rendered = project.work / "rendered" / "scene_001.mp4"
            stages = []

            def run_stage(stage, *_args, **_kwargs):
                stages.append(stage)
                if stage == "generate-video":
                    scene.write_text('Text("A", font="Noto Sans CJK JP")', encoding="utf-8")
                if stage == "self-check-video":
                    scene.write_text('Text("A", font="DejaVu Sans")', encoding="utf-8")
                if stage == "repair-commercial-fonts-1":
                    scene.write_text('Text("A", font="Noto Sans Math")', encoding="utf-8")
                    rendered.write_bytes(b"rerendered")
                return StageSummary(stage, 0, TokenUsage())

            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch.object(
                CodexRunner, "_run_stage", side_effect=run_stage
            ), redirect_stdout(StringIO()):
                CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"}).run_pipeline(request)
            self.assertEqual(stages[-3:], [
                "self-check-video", "repair-commercial-fonts-1", "self-check-video-font-repair-1",
            ])

            scene.write_text('Text("A", font="DejaVu Sans")', encoding="utf-8")
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch.object(
                CodexRunner, "_run_stage", return_value=StageSummary("stage", 0, TokenUsage())
            ), redirect_stdout(StringIO()):
                with self.assertRaisesRegex(CodexExecutionError, "修正できませんでした"):
                    CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"})._repair_font_issues(
                        [], 2, request
                    )

    def test_commercial_revision_repairs_font_before_self_check(self) -> None:
        with TemporaryDirectory() as temp:
            project, _ = self.make_project(Path(temp))
            (project.prompts / "revise-video.md").write_text("revise", encoding="utf-8")
            (project.prompts / "repair-commercial-fonts.md").write_text("repair", encoding="utf-8")
            target = project.output / "previous.mp4"
            target.touch()
            scene = project.work / "scenes" / "scene_001.py"
            rendered = project.work / "rendered" / "scene_001.mp4"
            stages = []

            def run_stage(stage, *_args, **kwargs):
                stages.append(stage)
                if stage == "revise-video":
                    scene.write_text('Text("A", font="DejaVu Sans")', encoding="utf-8")
                if stage == "repair-commercial-fonts-1":
                    self.assertIn("DejaVu Sans", kwargs["font_issue"])
                    scene.write_text('Text("A", font="Noto Sans CJK JP")', encoding="utf-8")
                    rendered.write_bytes(b"rerendered")
                return StageSummary(stage, 0, TokenUsage())

            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch.object(
                CodexRunner, "_run_stage", side_effect=run_stage
            ), redirect_stdout(StringIO()):
                CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"}).run_revision(
                    "修正", target
                )
            self.assertEqual(stages, ["revise-video", "repair-commercial-fonts-1", "self-check-video"])

    def test_commercial_repair_requires_updated_rendered_scene(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            scene = project.work / "scenes" / "scene_001.py"
            scene.write_text('Text("A", font="DejaVu Sans")', encoding="utf-8")
            stages = []

            def run_stage(stage, *_args, **_kwargs):
                stages.append(stage)
                scene.write_text('Text("A", font="Noto Sans CJK JP")', encoding="utf-8")
                return StageSummary(stage, 0, TokenUsage())

            with patch.object(CodexRunner, "_run_stage", side_effect=run_stage):
                with self.assertRaisesRegex(CodexExecutionError, "再レンダリング"):
                    CodexRunner(project, commercial_env={"FONTCONFIG_FILE": "/tmp/fonts.conf"})._repair_font_issues(
                        [], 2, request
                    )
            self.assertEqual(stages, ["repair-commercial-fonts-1", "repair-commercial-fonts-2"])

    def test_does_not_include_speaker_in_non_video_prompt(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            prompt = CodexRunner(project, speaker="四国めたん")._build_prompt(
                "research", project.prompts / "research.md", request
            )

        self.assertNotIn("ナレーション話者", prompt)

    def test_runs_revision_with_network_access_and_revision_context(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            revise_prompt = project.prompts / "revise-video.md"
            revise_prompt.write_text("# revise", encoding="utf-8")
            target = project.output / "20260101000000_topic.mp4"
            target.touch()
            events = [{"type": "turn.completed", "usage": {"input_tokens": 10}}]
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen", side_effect=[FakeCodexProcess(events) for _ in range(2)]
            ) as popen, redirect_stdout(StringIO()):
                CodexRunner(project, "fake-codex", "ずんだもん").run_revision(
                    "文字を大きくして", target
                )

            self.assertEqual(popen.call_count, 2)
            command = popen.call_args_list[0].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", command)
            self.assertIn("features.network_proxy.enabled=true", command)
            prompt = command[-1]
            self.assertIn("修正対象の完成動画: output/20260101000000_topic.mp4", prompt)
            self.assertIn("ユーザーの修正指示:\n文字を大きくして", prompt)
            self.assertIn("ナレーション話者: ずんだもん", prompt)
            self.assertTrue((project.logs / "revise-video.stdout.log").is_file())
            check_command = popen.call_args_list[1].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", check_command)
            self.assertIn("修正対象の完成動画: output/20260101000000_topic.mp4", check_command[-1])
            self.assertIn("ユーザーの修正指示:\n文字を大きくして", check_command[-1])
            self.assertIn("ナレーション話者: ずんだもん", check_command[-1])
            self.assertTrue((project.logs / "self-check-video.stdout.log").is_file())

    def test_stops_before_self_check_when_generation_fails(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            success = FakeCodexProcess([])
            failure = FakeCodexProcess([], returncode=1)
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen", side_effect=[success, success, failure]
            ) as popen, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                with self.assertRaises(CodexExecutionError):
                    CodexRunner(project).run_pipeline(request)

            self.assertEqual(popen.call_count, 3)
            self.assertFalse((project.logs / "self-check-video.stdout.log").exists())

    def test_stops_revision_when_self_check_fails(self) -> None:
        with TemporaryDirectory() as temp:
            project, _ = self.make_project(Path(temp))
            (project.prompts / "revise-video.md").write_text("# revise", encoding="utf-8")
            target = project.output / "original.mp4"
            target.touch()
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen",
                side_effect=[FakeCodexProcess([]), FakeCodexProcess([], returncode=1)],
            ) as popen, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                with self.assertRaises(CodexExecutionError):
                    CodexRunner(project).run_revision("修正", target)

            self.assertEqual(popen.call_count, 2)
            self.assertTrue((project.logs / "self-check-video.stdout.log").is_file())

    def test_stops_after_a_failed_stage(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            failed = FakeCodexProcess(
                [{"type": "turn.completed", "usage": {"input_tokens": 10}}],
                "failure\n",
                returncode=1,
            )
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.Popen", return_value=failed
            ) as popen, redirect_stdout(StringIO()) as stdout:
                with self.assertRaises(CodexExecutionError):
                    CodexRunner(project).run_pipeline(request)

            self.assertEqual(popen.call_count, 1)
            self.assertTrue((project.logs / "research.stderr.log").is_file())
            self.assertIn("input 10", stdout.getvalue())

    def test_marks_token_usage_unavailable_when_completion_event_has_no_usage(self) -> None:
        self.assertEqual(
            CodexRunner._format_usage(CodexRunner._usage_from_event(None)),
            "Codex トークン: 取得不可",
        )
        self.assertEqual(
            CodexRunner._format_usage(TokenUsage(input_tokens=1, available=True)),
            "Codex トークン: input 1, cached input 0, output 0, reasoning output 0",
        )
