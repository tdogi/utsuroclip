"""Isolated Noto font environment for commercial video rendering."""

from __future__ import annotations

from contextlib import contextmanager
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Iterator
from xml.sax.saxutils import escape


REQUIRED_FAMILIES = ("Noto Sans CJK JP", "Noto Sans Math")
ALLOWED_FAMILIES = (
    "Noto Sans CJK JP",
    "Noto Sans Mono CJK JP",
    "Noto Serif CJK JP",
    "Noto Sans Math",
)


class CommercialFontError(RuntimeError):
    """The commercial font policy cannot be satisfied."""


def installed_fonts() -> dict[str, set[Path]]:
    try:
        result = subprocess.run(
            ["fc-list", "-f", "%{family[0]}\t%{file}\n"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError as error:
        raise CommercialFontError("fontconfig の fc-list が見つかりません") from error
    if result.returncode:
        raise CommercialFontError(f"フォント一覧を取得できません: {result.stderr.strip()}")
    families: dict[str, set[Path]] = {}
    for line in result.stdout.splitlines():
        family, separator, filename = line.partition("\t")
        if separator and family in ALLOWED_FAMILIES:
            path = Path(filename)
            if path.is_file():
                families.setdefault(family, set()).add(path.resolve())
    return families


def font_codepoints(files: set[Path]) -> set[int]:
    codepoints: set[int] = set()
    for path in files:
        result = subprocess.run(
            ["fc-query", "-f", "%{charset}\n", str(path)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise CommercialFontError(f"フォントの文字情報を取得できません: {path}")
        for token in result.stdout.split():
            try:
                first, separator, last = token.partition("-")
                start = int(first, 16)
                end = int(last, 16) if separator else start
            except ValueError as error:
                raise CommercialFontError(f"フォントの文字情報が不正です: {path}") from error
            codepoints.update(range(start, end + 1))
    return codepoints


def validate_scene_sources(scene_directory: Path) -> None:
    """Reject font APIs that bypass the commercial rendering guard."""
    scenes = sorted(scene_directory.glob("scene_*.py"))
    if not scenes:
        raise CommercialFontError("商用利用モードの Manim シーンが見つかりません")
    for scene in scenes:
        try:
            tree = ast.parse(scene.read_text(encoding="utf-8"), filename=str(scene))
        except (OSError, SyntaxError) as error:
            raise CommercialFontError(f"シーンコードを確認できません: {scene} ({error})") from error
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else ""
            )
            if name in {"Tex", "MathTex", "register_font"}:
                raise CommercialFontError(
                    f"商用利用モードでは {name} のフォントを確認できません: {scene}"
                )
            if name in {"Text", "MarkupText"}:
                for keyword in node.keywords:
                    if keyword.arg == "font" and isinstance(keyword.value, ast.Constant):
                        if keyword.value.value not in ALLOWED_FAMILIES:
                            raise CommercialFontError(
                                f"商用利用モードで許可されていないフォントです: "
                                f"{keyword.value.value} ({scene})"
                            )


@contextmanager
def commercial_font_environment() -> Iterator[dict[str, str]]:
    """Expose only the approved installed fonts to fontconfig and Manim."""
    families = installed_fonts()
    missing = [name for name in REQUIRED_FAMILIES if name not in families]
    if missing:
        raise CommercialFontError(
            "商用利用モードに必要なフォントがありません: " + ", ".join(missing)
            + "。Ubuntu / WSL では sudo apt install fonts-noto-cjk fonts-noto-core を実行してください。"
        )
    files = set().union(*(families[name] for name in families))
    try:
        codepoints = font_codepoints(files)
    except FileNotFoundError as error:
        raise CommercialFontError("fontconfig の fc-query が見つかりません") from error
    if not codepoints:
        raise CommercialFontError("許可したフォントの文字情報を取得できません")

    with tempfile.TemporaryDirectory(prefix="utsuroclip-commercial-fonts-") as directory:
        root = Path(directory)
        font_dir = root / "fonts"
        font_dir.mkdir()
        for index, path in enumerate(sorted(files)):
            (font_dir / f"font-{index}{path.suffix}").symlink_to(path)
        config = root / "fonts.conf"
        config.write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
            f"<fontconfig><dir>{escape(str(font_dir))}</dir>"
            f"<cachedir>{escape(str(root / 'cache'))}</cachedir></fontconfig>",
            encoding="utf-8",
        )
        charset = root / "charset.json"
        charset.write_text(json.dumps(sorted(codepoints)), encoding="utf-8")
        hook = root / "sitecustomize.py"
        hook.write_text(
            "import os\nimport sys\n"
            "try:\n"
            "    from utsuroclip.font_guard import install_if_manim\n"
            "    install_if_manim()\n"
            "except BaseException as error:\n"
            "    print(f'商用利用モードのフォント検査を開始できません: {error}', file=sys.stderr)\n"
            "    os._exit(1)\n",
            encoding="utf-8",
        )
        package_src = str(Path(__file__).resolve().parents[1])
        python_path = os.pathsep.join(filter(None, (str(root), package_src, os.environ.get("PYTHONPATH"))))
        yield {
            "FONTCONFIG_FILE": str(config),
            "UTSUROCLIP_COMMERCIAL_CHARSET": str(charset),
            "UTSUROCLIP_COMMERCIAL_FAMILIES": json.dumps(sorted(families)),
            "PYTHONPATH": python_path,
        }
