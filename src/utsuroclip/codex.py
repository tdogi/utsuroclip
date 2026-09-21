"""Non-interactive Codex CLI integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from .project import ProjectPaths


class CodexExecutionError(RuntimeError):
    """Raised when a Codex stage cannot complete."""


@dataclass(frozen=True)
class CodexRunner:
    """Run the three artifact-producing stages through ``codex exec``."""

    project: ProjectPaths
    executable: str = "codex"

    STAGES = (
        ("research", "research.md"),
        ("write-script", "write-script.md"),
        ("generate-video", "generate-video.md"),
    )

    def run_pipeline(self, request: Path) -> None:
        if shutil.which(self.executable) is None:
            raise CodexExecutionError(
                f"Codex CLI が見つかりません: {self.executable}。README のセットアップ手順を確認してください。"
            )

        request = request.resolve()
        for stage, prompt_name in self.STAGES:
            self._run_stage(stage, self.project.prompts / prompt_name, request)

    def _run_stage(self, stage: str, prompt_path: Path, request: Path) -> None:
        prompt = self._build_prompt(stage, prompt_path, request)
        final_message = self.project.logs / f"{stage}.final.md"
        command = [
            self.executable,
            "exec",
            "--sandbox",
            "workspace-write",
        ]
        if stage == "generate-video":
            command.extend([
                "--config",
                "sandbox_workspace_write.network_access=true",
                "--config",
                "features.network_proxy.enabled=true",
                "--config",
                'features.network_proxy.domains={ "127.0.0.1" = "allow" }',
            ])
        command.extend(["--output-last-message", str(final_message), prompt])
        result = subprocess.run(
            command,
            cwd=self.project.root,
            text=True,
            capture_output=True,
            check=False,
        )
        (self.project.logs / f"{stage}.stdout.log").write_text(
            result.stdout, encoding="utf-8"
        )
        (self.project.logs / f"{stage}.stderr.log").write_text(
            result.stderr, encoding="utf-8"
        )
        if result.returncode != 0:
            raise CodexExecutionError(
                f"Codex の {stage} 工程が終了コード {result.returncode} で失敗しました。"
                f" ログ: {self.project.logs / (stage + '.stderr.log')}"
            )

    def _build_prompt(self, stage: str, prompt_path: Path, request: Path) -> str:
        instructions = prompt_path.read_text(encoding="utf-8").strip()
        try:
            request_label = request.relative_to(self.project.root)
        except ValueError:
            request_label = request
        return (
            f"{instructions}\n\n"
            "## 実行コンテキスト\n"
            f"- 現在の工程: {stage}\n"
            f"- プロジェクトルート: {self.project.root}\n"
            f"- 動画概要: {request_label}\n"
            "- このリポジトリの AGENTS.md と関連 Skill を必ず守ってください。\n"
            "- 指定された成果物を実際に保存し、完了後に保存先と実施内容を簡潔に報告してください。"
        )
