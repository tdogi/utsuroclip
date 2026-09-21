from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.codex import CodexExecutionError, CodexRunner
from utsuroclip.project import ProjectPaths


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
            completed = subprocess.CompletedProcess([], 0, stdout="done", stderr="progress")
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.run", return_value=completed
            ) as run:
                CodexRunner(project, "fake-codex").run_pipeline(request)

            self.assertEqual(run.call_count, 3)
            first_command = run.call_args_list[0].args[0]
            self.assertEqual(first_command[:4], ["fake-codex", "exec", "--sandbox", "workspace-write"])
            self.assertIn("--output-last-message", first_command)
            video_command = run.call_args_list[2].args[0]
            self.assertIn("sandbox_workspace_write.network_access=true", video_command)
            self.assertIn("features.network_proxy.enabled=true", video_command)
            self.assertIn('features.network_proxy.domains={ "127.0.0.1" = "allow" }', video_command)
            self.assertTrue((project.logs / "research.stdout.log").is_file())
            self.assertEqual((project.logs / "research.stderr.log").read_text(encoding="utf-8"), "progress")

    def test_stops_after_a_failed_stage(self) -> None:
        with TemporaryDirectory() as temp:
            project, request = self.make_project(Path(temp))
            failed = subprocess.CompletedProcess([], 1, stdout="", stderr="failure")
            with patch("utsuroclip.codex.shutil.which", return_value="/bin/codex"), patch(
                "utsuroclip.codex.subprocess.run", return_value=failed
            ) as run:
                with self.assertRaises(CodexExecutionError):
                    CodexRunner(project).run_pipeline(request)

            self.assertEqual(run.call_count, 1)
            self.assertTrue((project.logs / "research.stderr.log").is_file())
