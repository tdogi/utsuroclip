#!/usr/bin/env python3
"""Render one Manim scene and place its MP4 at a stable path."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manim シーンを MP4 へレンダリングします")
    parser.add_argument("scene_file", type=Path, help="Manim Python ファイル")
    parser.add_argument("scene_class", help="レンダリングする Scene クラス名")
    parser.add_argument("--output", type=Path, required=True, help="出力 MP4 パス")
    parser.add_argument("--manim-bin", default="manim", help="Manim 実行ファイル名またはパス")
    parser.add_argument("--quality", choices=("l", "m", "h", "p", "k"), default="h", help="Manim 品質")
    args = parser.parse_args(argv)
    if not args.scene_file.is_file():
        parser.error(f"シーンファイルが見つかりません: {args.scene_file}")
    if shutil.which(args.manim_bin) is None:
        print(f"Manim が見つかりません: {args.manim_bin}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="utsuroclip-manim-", dir=args.output.parent) as media_dir:
        command = [
            args.manim_bin,
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
