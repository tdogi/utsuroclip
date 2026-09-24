"""Command-line interface for UtsuroClip."""

from __future__ import annotations

import argparse
from contextlib import ExitStack, nullcontext
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unicodedata

from .codex import CodexExecutionError, CodexRunner
from .commercial_fonts import (
    CommercialFontError, commercial_font_environment, validate_scene_sources,
)
from .project import ProjectPaths, ProjectStateError


SPEAKERS = ("ずんだもん", "四国めたん", "春日部つむぎ")
DEFAULT_SPEAKER = "春日部つむぎ"


@dataclass(frozen=True)
class RevisionBackup:
    """Temporary backup of the production set changed by one revision."""

    project: ProjectPaths
    target_video: Path
    directory: Path
    previous_videos: set[Path]

    @property
    def work(self) -> Path:
        return self.directory / "work"

    @property
    def target(self) -> Path:
        return self.directory / "target.mp4"

    def create(self) -> None:
        shutil.copytree(self.project.work, self.work, symlinks=True)
        shutil.copy2(self.target_video, self.target)

    def restore(self) -> None:
        failed_logs = self.directory / "failed-logs"
        failed_logs.mkdir()
        for stage in ("revise-video", "self-check-video"):
            for log in self.project.logs.glob(f"{stage}.*"):
                if log.is_file():
                    shutil.copy2(log, failed_logs / log.name)

        shutil.rmtree(self.project.work)
        shutil.copytree(self.work, self.project.work, symlinks=True)
        shutil.copy2(self.target, self.target_video)
        for video in self.project.output.glob("*.mp4"):
            if video.is_file() and video.resolve() not in self.previous_videos:
                video.unlink()
        for log in failed_logs.iterdir():
            shutil.copy2(log, self.project.logs / log.name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utsuroclip", description="短尺の解説動画を生成します。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="動画概要から動画を生成する")
    generate.add_argument("request", type=Path, help="動画概要を記載した Markdown ファイル")
    generate.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="UtsuroClip プロジェクトのルート（既定値: カレントディレクトリ）",
    )
    generate.add_argument(
        "--codex-bin", default="codex", help="Codex CLI 実行ファイル名またはパス"
    )
    generate.add_argument(
        "--speaker",
        choices=SPEAKERS,
        default=DEFAULT_SPEAKER,
        help=f"ナレーション話者（既定値: {DEFAULT_SPEAKER}）",
    )
    generate.add_argument("--bgm", type=Path, help="完成動画に重ねる音楽ファイル")
    generate.add_argument(
        "--commercial", action="store_true", help="動画内のフォントを商用利用可能な Noto に制限する"
    )
    generate.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="中間成果物の削除を確認せずに実行する",
    )
    revise = subparsers.add_parser("revise", help="完成動画を修正する")
    revise.add_argument("-p", "--prompt", required=True, help="動画への修正指示")
    revise.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="UtsuroClip プロジェクトのルート（既定値: カレントディレクトリ）",
    )
    revise.add_argument(
        "--codex-bin", default="codex", help="Codex CLI 実行ファイル名またはパス"
    )
    return parser


def confirm_cleanup(project: ProjectPaths) -> bool:
    artifacts = project.intermediate_artifacts()
    if not artifacts:
        return True
    print("前回の中間成果物が残っています:", file=sys.stderr)
    for artifact in artifacts:
        print(f"- {artifact.relative_to(project.root)}", file=sys.stderr)
    try:
        answer = input("中間成果物を削除して続行しますか？ [y/N]: ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def safe_title(title: str) -> str:
    """Turn a Codex-provided title into a portable filename component."""
    if "\n" in title or "\r" in title:
        raise ValueError("タイトルは1行で指定してください")
    normalized = unicodedata.normalize("NFKC", title).strip()
    normalized = "".join(
        "_" if character in '<>:"/\\|?*' else character
        for character in normalized
        if unicodedata.category(character)[0] != "C"
    )
    normalized = " ".join(normalized.split()).strip(" ._")
    if not normalized:
        raise ValueError("タイトルが空か、ファイル名に使用できない文字だけです")
    return normalized[:80].rstrip(" .")


def final_video_path(project: ProjectPaths) -> Path:
    try:
        title = project.title_file.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise CodexExecutionError(
            f"Codex は完了しましたが動画タイトルを読み取れません: {project.title_file} ({error})"
        ) from error
    try:
        filename_title = safe_title(title)
    except ValueError as error:
        raise CodexExecutionError(f"Codex が生成した動画タイトルが不正です: {error}") from error
    return project.output / f"{datetime.now():%Y%m%d%H%M%S}_{filename_title}.mp4"


def generated_video_path(
    project: ProjectPaths, previous_videos: set[Path], label: str = "最終動画"
) -> Path:
    """Find the video produced by the just-completed Codex generation stage."""
    temporary_video = project.output / "video.mp4"
    if temporary_video.is_file():
        return temporary_video

    new_videos = sorted(
        (
            path
            for path in project.output.glob("*.mp4")
            if path.is_file() and path.resolve() not in previous_videos
        ),
        key=lambda path: path.name,
    )
    if len(new_videos) == 1:
        return new_videos[0]
    if not new_videos:
        raise CodexExecutionError(
            f"Codex は完了しましたが{label}が生成されていません: {temporary_video}"
        )
    filenames = ", ".join(path.name for path in new_videos)
    raise CodexExecutionError(
        "Codex が一時ファイル以外の動画を複数生成したため、"
        f"{label}を特定できません: "
        f"{filenames}"
    )


def revised_video_path(target: Path) -> Path:
    """Return a distinct, clearly marked output path for a revision."""
    return target.with_name(f"{target.stem}_revised_{datetime.now():%Y%m%d%H%M%S}.mp4")


def write_video_records(project: ProjectPaths, video: Path, speaker: str, commercial: bool = False) -> None:
    try:
        relative_video = video.relative_to(project.root)
    except ValueError as error:  # pragma: no cover - callers always use project.output
        raise CodexExecutionError(f"完成動画がプロジェクト外にあります: {video}") from error
    project.final_video_record.write_text(f"{relative_video}\n", encoding="utf-8")
    project.speaker_record.write_text(f"{speaker}\n", encoding="utf-8")
    project.commercial_mode_record.write_text(
        "commercial\n" if commercial else "standard\n", encoding="utf-8"
    )


def recorded_commercial_mode(project: ProjectPaths) -> bool:
    """Old production sets without a record were made in standard mode."""
    if not project.commercial_mode_record.exists():
        return False
    value = project.commercial_mode_record.read_text(encoding="utf-8").strip()
    if value not in {"commercial", "standard"}:
        raise CodexExecutionError(f"商用利用モードの記録が不正です: {value or '空'}")
    return value == "commercial"


def recorded_video_path(project: ProjectPaths) -> Path:
    try:
        recorded = project.final_video_record.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise CodexExecutionError(
            f"修正対象の動画記録を読み取れません: {project.final_video_record} ({error})"
        ) from error
    if not recorded or "\n" in recorded or "\r" in recorded:
        raise CodexExecutionError("修正対象の動画記録が不正です")
    candidate = (project.root / recorded).resolve()
    output_root = project.output.resolve()
    try:
        candidate.relative_to(output_root)
    except ValueError as error:
        raise CodexExecutionError("修正対象の動画記録は output/ 内を指している必要があります") from error
    if candidate.suffix.lower() != ".mp4" or not candidate.is_file():
        raise CodexExecutionError(f"修正対象の完成動画が見つかりません: {candidate}")
    return candidate


def recorded_speaker(project: ProjectPaths) -> str:
    try:
        speaker = project.speaker_record.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise CodexExecutionError(
            f"ナレーション話者の記録を読み取れません: {project.speaker_record} ({error})"
        ) from error
    if speaker not in SPEAKERS:
        raise CodexExecutionError(f"ナレーション話者の記録が不正です: {speaker or '空'}")
    return speaker


def validate_bgm(path: Path) -> None:
    if not path.is_file():
        raise CodexExecutionError(f"BGMファイルが見つかりません: {path}")
    if shutil.which("ffmpeg") is None:
        raise CodexExecutionError("BGMの確認に必要なFFmpegが見つかりません")
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-t", "0.1", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise CodexExecutionError(
            f"BGMの音声を読み取れません: {path} ({result.stderr.strip() or 'FFmpegエラー'})"
        )


def recorded_bgm(project: ProjectPaths) -> Path | None:
    if not project.bgm_record.exists():
        return None
    recorded = project.bgm_record.read_text(encoding="utf-8").strip()
    candidate = (project.root / recorded).resolve()
    try:
        candidate.relative_to((project.work / "audio").resolve())
    except ValueError as error:
        raise CodexExecutionError("BGMの記録は work/audio/ 内を指している必要があります") from error
    if not recorded or not candidate.is_file():
        raise CodexExecutionError(f"保存済みのBGMが見つかりません: {candidate}")
    return candidate


def mix_bgm(video: Path, bgm: Path) -> None:
    """Replace a narration-only video only after FFmpeg has mixed it successfully."""
    with tempfile.TemporaryDirectory(prefix="utsuroclip-bgm-", dir=video.parent) as directory:
        mixed = Path(directory) / "mixed.mp4"
        result = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", str(video), "-stream_loop", "-1", "-i", str(bgm),
                "-filter_complex",
                "[0:a:0]aresample=async=1:first_pts=0[voice];"
                "[1:a:0]volume=0.15,aresample=async=1:first_pts=0[music];"
                "[voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]",
                "-map", "0:v:0", "-map", "[mixed]", "-c:v", "copy", "-c:a", "aac",
                "-shortest", str(mixed),
            ],
            capture_output=True, text=True, check=False,
        )
        if result.returncode or not mixed.is_file():
            raise CodexExecutionError(
                f"BGMの適用に失敗しました: {result.stderr.strip() or 'FFmpegエラー'}"
            )
        mixed.replace(video)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "revise":
        return revise(args)
    if args.command != "generate":  # pragma: no cover - argparse guarantees this
        return 2

    root = args.project_root.resolve()
    request = args.request if args.request.is_absolute() else (Path.cwd() / args.request)
    request = request.resolve()
    if not request.is_file():
        print(f"動画概要ファイルが見つかりません: {request}", file=sys.stderr)
        return 2
    if request.suffix.lower() not in {".md", ".markdown"}:
        print("動画概要ファイルは Markdown（.md または .markdown）にしてください。", file=sys.stderr)
        return 2

    project = ProjectPaths(root)
    staged_bgm: Path | None = None
    font_stack = ExitStack()
    try:
        commercial_env = font_stack.enter_context(
            commercial_font_environment() if args.commercial else nullcontext(None)
        )
        if args.bgm is not None:
            bgm_source = args.bgm if args.bgm.is_absolute() else Path.cwd() / args.bgm
            bgm_source = bgm_source.resolve()
            validate_bgm(bgm_source)
            with tempfile.NamedTemporaryFile(suffix=bgm_source.suffix, delete=False) as handle:
                staged_bgm = Path(handle.name)
            shutil.copy2(bgm_source, staged_bgm)
        project.require_assets()
        if args.commercial:
            project.require_commercial_font_assets()
        if not args.yes and not confirm_cleanup(project):
            print("中間成果物の削除が確認されなかったため、生成を中断しました。", file=sys.stderr)
            return 1
        project.clean_intermediate_artifacts()
        project.prepare_workspace()
        retained_bgm = None
        if staged_bgm is not None:
            retained_bgm = project.work / "audio" / f"bgm{staged_bgm.suffix}"
            shutil.copy2(staged_bgm, retained_bgm)
            project.bgm_record.write_text(
                f"{retained_bgm.relative_to(project.root)}\n", encoding="utf-8"
            )
        previous_videos = {
            path.resolve() for path in project.output.glob("*.mp4") if path.is_file()
        }
        tools_before = project.tools_snapshot()
        try:
            CodexRunner(project, args.codex_bin, args.speaker, commercial_env).run_pipeline(request)
        finally:
            project.require_tools_unchanged(tools_before)
        if args.commercial:
            validate_scene_sources(project.work / "scenes")
        generated_video = generated_video_path(project, previous_videos)
        final_video = final_video_path(project)
        if generated_video != final_video and final_video.exists():
            raise CodexExecutionError(
                f"同名の完成動画が既に存在するため上書きしません: {final_video}"
            )
        if retained_bgm is not None:
            mix_bgm(generated_video, retained_bgm)
        if generated_video != final_video:
            generated_video.rename(final_video)
        write_video_records(project, final_video, args.speaker, args.commercial)
    except (FileNotFoundError, CodexExecutionError, CommercialFontError, OSError, ProjectStateError) as error:
        print(f"生成に失敗しました: {error}", file=sys.stderr)
        return 1
    finally:
        font_stack.close()
        if staged_bgm is not None:
            staged_bgm.unlink(missing_ok=True)

    print(f"生成完了: {final_video}")
    print(f"工程ログ: {project.logs}")
    return 0


def revise(args: argparse.Namespace) -> int:
    project = ProjectPaths(args.project_root.resolve())
    font_stack = ExitStack()
    try:
        project.require_revision_assets()
        target_video = recorded_video_path(project)
        speaker = recorded_speaker(project)
        commercial = recorded_commercial_mode(project)
        if commercial:
            project.require_commercial_font_assets()
        bgm = recorded_bgm(project)
        temporary_video = project.output / "video.mp4"
        if temporary_video.exists():
            raise CodexExecutionError(
                f"前回の未完了一時動画が残っています: {temporary_video}。"
                "内容を確認してから削除し、再度実行してください。"
            )
        previous_videos = {
            path.resolve() for path in project.output.glob("*.mp4") if path.is_file()
        }
        commercial_env = font_stack.enter_context(
            commercial_font_environment() if commercial else nullcontext(None)
        )
        backup = RevisionBackup(
            project,
            target_video,
            Path(tempfile.mkdtemp(prefix="utsuroclip-revise-")),
            previous_videos,
        )
        return _revise_with_fonts(
            args, project, target_video, speaker, bgm, backup, previous_videos, commercial_env
        )
    except (FileNotFoundError, CodexExecutionError, CommercialFontError, OSError, ProjectStateError) as error:
        print(f"修正に失敗しました: {error}", file=sys.stderr)
        return 1
    finally:
        font_stack.close()


def _revise_with_fonts(
    args: argparse.Namespace,
    project: ProjectPaths,
    target_video: Path,
    speaker: str,
    bgm: Path | None,
    backup: RevisionBackup,
    previous_videos: set[Path],
    commercial_env: dict[str, str] | None,
) -> int:
    commercial = commercial_env is not None
    try:
        backup.create()
    except OSError:
        shutil.rmtree(backup.directory, ignore_errors=True)
        raise
    try:
        tools_before = project.tools_snapshot()
        try:
            CodexRunner(project, args.codex_bin, speaker, commercial_env).run_revision(args.prompt, target_video)
        finally:
            project.require_tools_unchanged(tools_before)
        if commercial:
            validate_scene_sources(project.work / "scenes")
        generated_video = generated_video_path(project, previous_videos, "修正版の動画")
        revised_video = revised_video_path(target_video)
        if generated_video != revised_video and revised_video.exists():
            raise CodexExecutionError(
                f"同名の修正版動画が既に存在するため上書きしません: {revised_video}"
            )
        if bgm is not None:
            mix_bgm(generated_video, bgm)
        if generated_video != revised_video:
            generated_video.rename(revised_video)
        write_video_records(project, revised_video, speaker, commercial)
    except Exception as error:
        try:
            backup.restore()
        except OSError as restore_error:
            print(
                f"修正に失敗しました: {error}。"
                f"さらに修正前の制作素材の復元に失敗しました: {restore_error}。"
                f"バックアップ: {backup.directory}",
                file=sys.stderr,
            )
            return 1
        shutil.rmtree(backup.directory, ignore_errors=True)
        print(
            f"修正に失敗しました: {error}。修正前の制作素材を復元しました。",
            file=sys.stderr,
        )
        return 1
    shutil.rmtree(backup.directory, ignore_errors=True)
    print(f"修正完了: {revised_video}")
    print(f"工程ログ: {project.logs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
