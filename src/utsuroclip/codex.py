"""Non-interactive Codex CLI integration with live progress reporting."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from queue import Empty, Queue
import shutil
import subprocess
import sys
from threading import Thread
from time import monotonic
from typing import Iterator, TextIO

from .commercial_fonts import CommercialFontError, validate_scene_sources
from .project import ProjectPaths


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by a completed Codex turn."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    available: bool = False

    def add(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_output_tokens=(
                self.reasoning_output_tokens + other.reasoning_output_tokens
            ),
            available=self.available or other.available,
        )


@dataclass(frozen=True)
class StageSummary:
    """Measured result of a single Codex pipeline stage."""

    stage: str
    elapsed_seconds: float
    usage: TokenUsage


class CodexExecutionError(RuntimeError):
    """Raised when a Codex stage cannot complete."""

    def __init__(self, message: str, summary: StageSummary | None = None) -> None:
        super().__init__(message)
        self.summary = summary


@dataclass(frozen=True)
class CodexRunner:
    """Run artifact-producing and self-check stages through ``codex exec``."""

    project: ProjectPaths
    executable: str = "codex"
    speaker: str = "春日部つむぎ"
    commercial_env: dict[str, str] | None = None
    FONT_REPAIR_LIMIT = 2

    STAGES = (
        ("research", "research.md"),
        ("write-script", "write-script.md"),
        ("generate-video", "generate-video.md"),
        ("self-check-video", "self-check-video.md"),
    )

    def run_pipeline(self, request: Path) -> None:
        if shutil.which(self.executable) is None:
            raise CodexExecutionError(
                f"Codex CLI が見つかりません: {self.executable}。README のセットアップ手順を確認してください。"
            )

        request = request.resolve()
        summaries: list[StageSummary] = []
        started_at = monotonic()
        repairs_left = self.FONT_REPAIR_LIMIT
        try:
            for stage, prompt_name in self.STAGES:
                summaries.append(
                    self._run_stage(stage, self.project.prompts / prompt_name, request)
                )
                if self.commercial_env and stage == "generate-video":
                    repairs_left, _ = self._repair_font_issues(summaries, repairs_left, request)
                if self.commercial_env and stage == "self-check-video":
                    repairs_left = self._finish_commercial_fonts(
                        summaries, repairs_left, request=request
                    )
        except CodexExecutionError as error:
            if error.summary is not None:
                summaries.append(error.summary)
            raise
        finally:
            self._print_pipeline_summary(summaries, monotonic() - started_at)

    def run_revision(self, instruction: str, target_video: Path) -> None:
        """Ask Codex to revise the retained production set and render a new video."""
        if shutil.which(self.executable) is None:
            raise CodexExecutionError(
                f"Codex CLI が見つかりません: {self.executable}。README のセットアップ手順を確認してください。"
            )

        started_at = monotonic()
        summaries: list[StageSummary] = []
        repairs_left = self.FONT_REPAIR_LIMIT
        try:
            summaries.append(
                self._run_stage(
                    "revise-video",
                    self.project.prompts / "revise-video.md",
                    revision_instruction=instruction,
                    target_video=target_video,
                )
            )
            if self.commercial_env:
                repairs_left, _ = self._repair_font_issues(
                    summaries, repairs_left, revision_instruction=instruction,
                    target_video=target_video,
                )
            summaries.append(
                self._run_stage(
                    "self-check-video",
                    self.project.prompts / "self-check-video.md",
                    revision_instruction=instruction,
                    target_video=target_video,
                )
            )
            if self.commercial_env:
                self._finish_commercial_fonts(
                    summaries, repairs_left, revision_instruction=instruction,
                    target_video=target_video,
                )
        except CodexExecutionError as error:
            if error.summary is not None:
                summaries.append(error.summary)
            raise
        finally:
            self._print_pipeline_summary(summaries, monotonic() - started_at)

    def _repair_font_issues(
        self,
        summaries: list[StageSummary],
        repairs_left: int,
        request: Path | None = None,
        revision_instruction: str | None = None,
        target_video: Path | None = None,
    ) -> tuple[int, bool]:
        repaired = False
        rendered_before: dict[Path, int] | None = None
        while True:
            try:
                validate_scene_sources(self.project.work / "scenes")
                if rendered_before is not None and self._rendered_snapshot() == rendered_before:
                    raise CommercialFontError(
                        "フォントの修正後にシーン映像が再レンダリングされていません"
                    )
                return repairs_left, repaired
            except CommercialFontError as error:
                if repairs_left == 0:
                    raise CodexExecutionError(
                        f"商用利用モードのフォント違反を修正できませんでした: {error}"
                    ) from error
                attempt = self.FONT_REPAIR_LIMIT - repairs_left + 1
                repairs_left -= 1
                repaired = True
                rendered_before = self._rendered_snapshot()
                summaries.append(self._run_stage(
                    f"repair-commercial-fonts-{attempt}",
                    self.project.prompts / "repair-commercial-fonts.md",
                    request,
                    revision_instruction,
                    target_video,
                    font_issue=str(error),
                ))

    def _rendered_snapshot(self) -> dict[Path, int]:
        return {
            path: path.stat().st_mtime_ns
            for path in (self.project.work / "rendered").glob("scene_*.mp4")
            if path.is_file()
        }

    def _finish_commercial_fonts(
        self,
        summaries: list[StageSummary],
        repairs_left: int,
        request: Path | None = None,
        revision_instruction: str | None = None,
        target_video: Path | None = None,
    ) -> int:
        while True:
            repairs_left, repaired = self._repair_font_issues(
                summaries, repairs_left, request, revision_instruction, target_video
            )
            if not repaired:
                return repairs_left
            attempt = self.FONT_REPAIR_LIMIT - repairs_left
            summaries.append(self._run_stage(
                f"self-check-video-font-repair-{attempt}",
                self.project.prompts / "self-check-video.md",
                request,
                revision_instruction,
                target_video,
            ))

    def _run_stage(
        self,
        stage: str,
        prompt_path: Path,
        request: Path | None = None,
        revision_instruction: str | None = None,
        target_video: Path | None = None,
        font_issue: str | None = None,
    ) -> StageSummary:
        prompt = self._build_prompt(
            stage, prompt_path, request, revision_instruction, target_video, font_issue
        )
        final_message = self.project.logs / f"{stage}.final.md"
        stdout_log = self.project.logs / f"{stage}.stdout.log"
        stderr_log = self.project.logs / f"{stage}.stderr.log"
        command = [
            self.executable,
            "exec",
            "--sandbox",
            "workspace-write",
            "--json",
        ]
        if self._is_video_stage(stage):
            command.extend([
                "--config",
                "sandbox_workspace_write.network_access=true",
                "--config",
                "features.network_proxy.enabled=true",
                "--config",
                'features.network_proxy.domains={ "127.0.0.1" = "allow" }',
            ])
        command.extend(["--output-last-message", str(final_message), prompt])

        print(f"工程開始: {stage}", flush=True)
        started_at = monotonic()
        options = {}
        if self.commercial_env and self._is_video_stage(stage):
            options["env"] = {**os.environ, **self.commercial_env}
        process = subprocess.Popen(
            command,
            cwd=self.project.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            **options,
        )
        usage = TokenUsage()
        with stdout_log.open("w", encoding="utf-8") as stdout_file, stderr_log.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            for source, line in self._stream_process_output(process):
                if source == "stdout":
                    stdout_file.write(line)
                    stdout_file.flush()
                    usage = usage.add(self._report_json_event(stage, line))
                else:
                    stderr_file.write(line)
                    stderr_file.flush()
                    self._report_stderr_line(stage, line)

        summary = StageSummary(stage, monotonic() - started_at, usage)
        if process.returncode != 0:
            print(
                f"工程失敗: {stage} ({self._format_duration(summary.elapsed_seconds)})",
                file=sys.stderr,
                flush=True,
            )
            raise CodexExecutionError(
                f"Codex の {stage} 工程が終了コード {process.returncode} で失敗しました。"
                f" ログ: {stderr_log}",
                summary,
            )

        print(
            f"工程完了: {stage} ({self._format_duration(summary.elapsed_seconds)})",
            flush=True,
        )
        return summary

    @staticmethod
    def _is_video_stage(stage: str) -> bool:
        return stage in {"generate-video", "revise-video", "self-check-video"} or stage.startswith(
            ("repair-commercial-fonts-", "self-check-video-font-repair-")
        )

    def _stream_process_output(
        self, process: subprocess.Popen[str]
    ) -> Iterator[tuple[str, str]]:
        """Read both pipes concurrently so progress remains live and ordered per pipe."""
        if process.stdout is None or process.stderr is None:  # pragma: no cover
            raise RuntimeError("Codex の出力ストリームを開けませんでした。")

        events: Queue[tuple[str, str]] = Queue()
        readers = [
            Thread(target=self._enqueue_lines, args=("stdout", process.stdout, events)),
            Thread(target=self._enqueue_lines, args=("stderr", process.stderr, events)),
        ]
        for reader in readers:
            reader.start()

        while any(reader.is_alive() for reader in readers) or not events.empty():
            try:
                yield events.get(timeout=0.1)
            except Empty:
                continue
        for reader in readers:
            reader.join()
        process.wait()

    @staticmethod
    def _enqueue_lines(
        source: str, stream: TextIO, events: Queue[tuple[str, str]]
    ) -> None:
        for line in stream:
            events.put((source, line))
        stream.close()

    def _report_json_event(self, stage: str, line: str) -> TokenUsage:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return TokenUsage()

        event_type = event.get("type")
        if event_type == "thread.started":
            print(f"[{stage}] Codex セッションを開始しました", flush=True)
        elif event_type == "turn.started":
            print(f"[{stage}] Codex が処理を開始しました", flush=True)
        elif event_type == "item.started":
            self._report_started_item(stage, event.get("item"))
        elif event_type == "item.completed":
            self._report_completed_item(stage, event.get("item"))
        elif event_type == "turn.completed":
            return self._usage_from_event(event.get("usage"))
        elif event_type == "turn.failed":
            print(f"[{stage}] Codex のターンが失敗しました", file=sys.stderr, flush=True)
        return TokenUsage()

    def _report_started_item(self, stage: str, item: object) -> None:
        if not isinstance(item, dict):
            return
        item_type = item.get("type")
        if item_type == "command_execution":
            command = item.get("command")
            if isinstance(command, str):
                print(f"[{stage}] 実行: {self._shorten(command)}", flush=True)
        elif item_type == "web_search":
            query = item.get("query")
            if isinstance(query, str):
                print(f"[{stage}] Web 検索: {self._shorten(query)}", flush=True)
        elif item_type == "mcp_tool_call":
            tool = item.get("tool") or item.get("name")
            if isinstance(tool, str):
                print(f"[{stage}] ツール実行: {self._shorten(tool)}", flush=True)

    def _report_completed_item(self, stage: str, item: object) -> None:
        if not isinstance(item, dict) or item.get("type") != "agent_message":
            return
        message = item.get("text")
        if isinstance(message, str) and message.strip():
            print(f"[{stage}] Codex: {self._shorten(message)}", flush=True)

    @staticmethod
    def _report_stderr_line(stage: str, line: str) -> None:
        text = line.rstrip()
        if text:
            print(f"[{stage}] {text}", file=sys.stderr, flush=True)

    @staticmethod
    def _usage_from_event(value: object) -> TokenUsage:
        if not isinstance(value, dict):
            return TokenUsage()
        return TokenUsage(
            input_tokens=CodexRunner._integer(value.get("input_tokens")),
            cached_input_tokens=CodexRunner._integer(value.get("cached_input_tokens")),
            output_tokens=CodexRunner._integer(value.get("output_tokens")),
            reasoning_output_tokens=CodexRunner._integer(
                value.get("reasoning_output_tokens")
            ),
            available=True,
        )

    @staticmethod
    def _integer(value: object) -> int:
        return value if isinstance(value, int) and value >= 0 else 0

    def _print_pipeline_summary(
        self, summaries: list[StageSummary], elapsed_seconds: float
    ) -> None:
        print("Codex 実行サマリー:", flush=True)
        total_usage = TokenUsage()
        for summary in summaries:
            total_usage = total_usage.add(summary.usage)
            print(
                f"- {summary.stage}: {self._format_duration(summary.elapsed_seconds)} / "
                f"{self._format_usage(summary.usage)}",
                flush=True,
            )
        print(
            f"合計: {self._format_duration(elapsed_seconds)} / "
            f"{self._format_usage(total_usage)}",
            flush=True,
        )

    @staticmethod
    def _format_duration(elapsed_seconds: float) -> str:
        if elapsed_seconds < 60:
            return f"{elapsed_seconds:.1f}秒"
        minutes, seconds = divmod(int(elapsed_seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}時間{minutes}分{seconds}秒"
        return f"{minutes}分{seconds}秒"

    @staticmethod
    def _format_usage(usage: TokenUsage) -> str:
        if not usage.available:
            return "Codex トークン: 取得不可"
        return (
            "Codex トークン: "
            f"input {usage.input_tokens:,}, "
            f"cached input {usage.cached_input_tokens:,}, "
            f"output {usage.output_tokens:,}, "
            f"reasoning output {usage.reasoning_output_tokens:,}"
        )

    @staticmethod
    def _shorten(value: str, limit: int = 160) -> str:
        compact = " ".join(value.split())
        return compact if len(compact) <= limit else compact[: limit - 1] + "…"

    def _build_prompt(
        self,
        stage: str,
        prompt_path: Path,
        request: Path | None = None,
        revision_instruction: str | None = None,
        target_video: Path | None = None,
        font_issue: str | None = None,
    ) -> str:
        instructions = prompt_path.read_text(encoding="utf-8").strip()
        request_context = ""
        if request is not None:
            try:
                request_label = request.relative_to(self.project.root)
            except ValueError:
                request_label = request
            request_context = f"- 動画概要: {request_label}\n"
        speaker_context = ""
        if self._is_video_stage(stage):
            speaker_context = (
                f"- ナレーション話者: {self.speaker}\n"
                "- ナレーション話者に指定された名前を "
                "`python tools/voicevox.py --speaker` へ必ず渡してください。\n"
            )
        commercial_context = ""
        if self.commercial_env and self._is_video_stage(stage):
            commercial_context = (
                "- 商用利用モード: 有効。動画内の文字には Noto Sans CJK JP、"
                "Noto Sans Mono CJK JP、Noto Serif CJK JP、Noto Sans Math のみを使用してください。\n"
                "- 数式記号は Text と Noto Sans Math で描画し、Tex / MathTex と"
                " 未確認フォントを使用しないでください。\n"
                "- 未許可フォントや未対応文字でレンダリングが失敗したら、"
                "許可済みフォントや表現に修正して再レンダリングしてください。"
                "解消できない場合だけ工程を失敗として報告してください。\n"
            )
        font_issue_context = f"- 検出したフォントの問題: {font_issue}\n" if font_issue else ""
        revision_context = ""
        if revision_instruction is not None or target_video is not None:
            if revision_instruction is None or target_video is None:  # pragma: no cover
                raise ValueError("修正工程には指示と対象動画の両方が必要です")
            try:
                target_label = target_video.relative_to(self.project.root)
            except ValueError:
                target_label = target_video
            revision_context = (
                f"- 修正対象の完成動画: {target_label}\n"
                "- ユーザーの修正指示:\n"
                f"{revision_instruction}\n"
            )
        return (
            f"{instructions}\n\n"
            "## 実行コンテキスト\n"
            f"- 現在の工程: {stage}\n"
            f"- プロジェクトルート: {self.project.root}\n"
            f"{request_context}"
            f"{speaker_context}"
            f"{commercial_context}"
            f"{font_issue_context}"
            f"{revision_context}"
            "- このリポジトリの AGENTS.md と関連 Skill を必ず守ってください。\n"
            "- 指定された成果物を実際に保存し、完了後に保存先と実施内容を簡潔に報告してください。"
        )
