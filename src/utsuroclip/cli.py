"""Command-line interface for UtsuroClip."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

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
    return parser


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
        project.prepare_workspace()
        CodexRunner(project, args.codex_bin, args.speaker).run_pipeline(request)
        final_video = project.output / "video.mp4"
        if not final_video.is_file():
            raise CodexExecutionError(
                f"Codex は完了しましたが最終動画が生成されていません: {final_video}"
            )
    except (FileNotFoundError, CodexExecutionError, OSError) as error:
        print(f"生成に失敗しました: {error}", file=sys.stderr)
        return 1

    print(f"生成完了: {final_video}")
    print(f"工程ログ: {project.logs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
