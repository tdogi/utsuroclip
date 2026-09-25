#!/usr/bin/env python3
"""Render one Manim scene and place its MP4 at a stable path."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SUPPORTED_MANIM_VERSION = "0.21.0"


def require_supported_manim(executable: str) -> str | None:
    resolved = shutil.which(executable)
    if resolved is None:
        print(f"Manim が見つかりません: {executable}", file=sys.stderr)
        return None
    result = subprocess.run(
        [resolved, "--silent", "--version"], text=True, capture_output=True, check=False
    )
    version_output = result.stdout + result.stderr
    if result.returncode != 0 or f"v{SUPPORTED_MANIM_VERSION}" not in version_output:
        actual = version_output.strip() or "バージョンを取得できませんでした"
        print(
            f"対応する Manim Community Edition は v{SUPPORTED_MANIM_VERSION} です: {actual}",
            file=sys.stderr,
        )
        return None
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manim シーンを MP4 へレンダリングします")
    parser.add_argument("scene_file", type=Path, help="Manim Python ファイル")
    parser.add_argument("scene_class", help="レンダリングする Scene クラス名")
    parser.add_argument("--output", type=Path, required=True, help="出力 MP4 パス")
    parser.add_argument("--manim-bin", default="manim", help="Manim 実行ファイル名またはパス")
    parser.add_argument("--quality", choices=("l", "m", "h", "p", "k"), default="p", help="Manim 品質")
    args = parser.parse_args(argv)
    if not args.scene_file.is_file():
        parser.error(f"シーンファイルが見つかりません: {args.scene_file}")
    manim_bin = require_supported_manim(args.manim_bin)
    if manim_bin is None:
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="utsuroclip-manim-", dir=args.output.parent) as media_dir:
        command = [
            manim_bin,
            "--silent",
            f"-q{args.quality}",
            "--format",
            "mp4",
            "--media_dir",
            media_dir,
            "--output_file",
            args.output.stem,
            str(args.scene_file),
            args.scene_class,
        ]
        result = subprocess.run(command, text=True, check=False)
        if result.returncode != 0:
            return result.returncode
        rendered = list(Path(media_dir).rglob(f"{args.output.stem}.mp4"))
        if len(rendered) != 1:
            print("Manim の出力 MP4 を一意に特定できませんでした。", file=sys.stderr)
            return 1
        shutil.copy2(rendered[0], args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
