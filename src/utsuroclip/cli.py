"""Command-line interface for UtsuroClip."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import unicodedata

from .codex import CodexExecutionError, CodexRunner
from .project import ProjectPaths


SPEAKERS = ("ずんだもん", "四国めたん", "春日部つむぎ")
DEFAULT_SPEAKER = "春日部つむぎ"


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
    generate.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="中間成果物の削除を確認せずに実行する",
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    try:
        project.require_assets()
        if not args.yes and not confirm_cleanup(project):
            print("中間成果物の削除が確認されなかったため、生成を中断しました。", file=sys.stderr)
            return 1
        project.clean_intermediate_artifacts()
        project.prepare_workspace()
        CodexRunner(project, args.codex_bin, args.speaker).run_pipeline(request)
        temporary_video = project.output / "video.mp4"
        if not temporary_video.is_file():
            raise CodexExecutionError(
                f"Codex は完了しましたが最終動画が生成されていません: {temporary_video}"
            )
        final_video = final_video_path(project)
        if final_video.exists():
            raise CodexExecutionError(
                f"同名の完成動画が既に存在するため上書きしません: {final_video}"
            )
        temporary_video.rename(final_video)
    except (FileNotFoundError, CodexExecutionError, OSError) as error:
        print(f"生成に失敗しました: {error}", file=sys.stderr)
        return 1

    print(f"生成完了: {final_video}")
    print(f"工程ログ: {project.logs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
