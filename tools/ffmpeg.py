#!/usr/bin/env python3
"""Mux narrated scenes and concatenate them with FFmpeg."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def require_ffmpeg(executable: str) -> bool:
    if shutil.which(executable) is not None:
        return True
    print(f"FFmpeg が見つかりません: {executable}", file=sys.stderr)
    return False


def run(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode


def mux(args: argparse.Namespace) -> int:
    if not args.video.is_file() or not args.audio.is_file():
        print("入力映像または音声が見つかりません。", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    return run([
        args.ffmpeg_bin, "-y", "-i", str(args.video), "-i", str(args.audio),
        "-c:v", "copy", "-c:a", "aac", "-shortest", str(args.output),
    ])


def concat(args: argparse.Namespace) -> int:
    if len(args.videos) < 1 or any(not video.is_file() for video in args.videos):
        print("連結対象の MP4 が見つかりません。", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        manifest = Path(handle.name)
        for video in args.videos:
            escaped = str(video.resolve()).replace("'", r"'\\''")
            handle.write(f"file '{escaped}'\n")
    try:
        return run([
            args.ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", str(args.output),
        ])
    finally:
        manifest.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FFmpeg で UtsuroClip の映像を結合します")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="FFmpeg 実行ファイル名またはパス")
    commands = parser.add_subparsers(dest="command", required=True)
    mux_parser = commands.add_parser("mux", help="映像と音声を結合する")
    mux_parser.add_argument("--video", type=Path, required=True)
    mux_parser.add_argument("--audio", type=Path, required=True)
    mux_parser.add_argument("--output", type=Path, required=True)
    concat_parser = commands.add_parser("concat", help="複数の映像を連結する")
    concat_parser.add_argument("videos", type=Path, nargs="+")
    concat_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not require_ffmpeg(args.ffmpeg_bin):
        return 1
    return mux(args) if args.command == "mux" else concat(args)


if __name__ == "__main__":
    raise SystemExit(main())
