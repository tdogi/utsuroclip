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

from utsuroclip.codex import CodexExecutionError, CodexRunner, TokenUsage
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
        for name in ("research.md", "write-script.md", "generate-video.md"):
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
                side_effect=[FakeCodexProcess(events, "progress\n") for _ in range(3)],
            ) as popen, redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()) as stderr:
                CodexRunner(project, "fake-codex").run_pipeline(request)

            self.assertEqual(popen.call_count, 3)
            first_command = popen.call_args_list[0].args[0]
            self.assertEqual(first_command[:4], ["fake-codex", "exec", "--sandbox", "workspace-write"])
            self.assertIn("--json", first_command)
            self.assertIn("--output-last-message", first_command)
            video_command = popen.call_args_list[2].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", video_command)
            self.assertIn("features.network_proxy.enabled=true", video_command)
            self.assertIn('features.network_proxy.domains={ "127.0.0.1" = "allow" }', video_command)
            self.assertTrue((project.logs / "research.stdout.log").is_file())
            self.assertIn('"turn.completed"', (project.logs / "research.stdout.log").read_text(encoding="utf-8"))
            self.assertEqual((project.logs / "research.stderr.log").read_text(encoding="utf-8"), "progress\n")
            self.assertIn("[research] 実行: manim scene.py", stdout.getvalue())
            self.assertIn("input 300", stdout.getvalue())
            self.assertIn("[research] progress", stderr.getvalue())

    def test_includes_selected_speaker_in_video_generation_prompt(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            prompt = CodexRunner(project, speaker="四国めたん")._build_prompt(
                "generate-video", project.prompts / "generate-video.md", request
            )

        self.assertIn("ナレーション話者: 四国めたん", prompt)
        self.assertIn("--speaker", prompt)

    def test_does_not_include_speaker_in_non_video_prompt(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            prompt = CodexRunner(project, speaker="四国めたん")._build_prompt(
                "research", project.prompts / "research.md", request
            )

        self.assertNotIn("ナレーション話者", prompt)

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
