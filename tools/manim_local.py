#!/usr/bin/env python3
"""Offline-compatible Manim CLI subset used by tools/manim_renderer.py.

Manim 0.21's CLI performs an online package lookup in this environment.  This
small adapter accepts the arguments emitted by manim_renderer.py and invokes
the already-installed rendering API directly.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

from manim import Scene, config


QUALITY = {
    "l": "low_quality",
    "m": "medium_quality",
    "h": "high_quality",
    "p": "production_quality",
    "k": "fourk_quality",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    quality_group = parser.add_mutually_exclusive_group(required=True)
    for key, value in QUALITY.items():
        quality_group.add_argument(f"-q{key}", dest="quality", action="store_const", const=value)
    parser.add_argument("--format", default="mp4")
    parser.add_argument("--media_dir", type=Path, required=True)
    parser.add_argument("--output_file", required=True)
    parser.add_argument("scene_file", type=Path)
    parser.add_argument("scene_class")
    args = parser.parse_args()

    config.quality = args.quality
    config.format = args.format
    config.media_dir = str(args.media_dir)
    config.output_file = args.output_file
    config.disable_caching = True

    scene_path = args.scene_file.resolve()
    sys.path.insert(0, str(scene_path.parent))
    spec = importlib.util.spec_from_file_location(scene_path.stem, scene_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"シーンを読み込めません: {scene_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scene_type = getattr(module, args.scene_class)
    if not isinstance(scene_type, type) or not issubclass(scene_type, Scene):
        raise TypeError(f"Scene サブクラスではありません: {args.scene_class}")
    scene_type().render()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
