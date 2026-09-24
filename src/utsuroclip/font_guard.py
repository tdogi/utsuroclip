"""Check the actual strings passed to Manim's text constructors."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys

from .commercial_fonts import ALLOWED_FAMILIES


def validate_text(value: str, codepoints: set[int]) -> None:
    missing = sorted({
        character for character in value
        if character not in "\n\r\t" and ord(character) not in codepoints
    })
    if missing:
        names = ", ".join(f"{character} (U+{ord(character):04X})" for character in missing)
        raise RuntimeError(f"商用利用モードの Noto フォントにない文字です: {names}")


def install_if_manim() -> None:
    """Called from sitecustomize in the child Manim executable only."""
    if Path(sys.argv[0]).stem != "manim":
        return
    charset_path = os.environ.get("UTSUROCLIP_COMMERCIAL_CHARSET")
    if not charset_path:
        return
    import manim

    codepoints = set(json.loads(Path(charset_path).read_text(encoding="utf-8")))
    installed_families = set(json.loads(os.environ["UTSUROCLIP_COMMERCIAL_FAMILIES"]))
    for cls, markup in ((manim.Text, False), (manim.MarkupText, True)):
        original = cls.__init__

        def checked(self, *args, _original=original, _markup=markup, **kwargs):
            value = args[0] if args else kwargs.get("text", "")
            if not isinstance(value, str):
                raise RuntimeError("商用利用モードで文字列以外のテキストを描画できません")
            if _markup and re.search(r"\bfont(?:_desc|_family)?\s*=", value, re.IGNORECASE):
                raise RuntimeError("商用利用モードでは MarkupText の font_desc 等の指定を使用できません")
            family = kwargs.get("font") or "Noto Sans CJK JP"
            if family not in ALLOWED_FAMILIES:
                raise RuntimeError(f"商用利用モードで許可されていないフォントです: {family}")
            if family not in installed_families:
                raise RuntimeError(f"商用利用モードで必要なフォントがありません: {family}")
            for local_family in (kwargs.get("t2f") or {}).values():
                if local_family not in ALLOWED_FAMILIES or local_family not in installed_families:
                    raise RuntimeError(
                        f"商用利用モードで許可されていない部分指定フォントです: {local_family}"
                    )
            validate_text(html.unescape(value), codepoints)
            kwargs["font"] = family
            return _original(self, *args, **kwargs)

        cls.__init__ = checked

    for cls in (manim.Tex, manim.MathTex):
        def rejected(self, *args, **kwargs):
            raise RuntimeError(
                "商用利用モードでは Tex / MathTex のフォントを確認できません。"
                "Text と Noto Sans Math の文字を使用してください。"
            )

        cls.__init__ = rejected

    if hasattr(manim, "register_font"):
        def reject_font_registration(*args, **kwargs):
            raise RuntimeError("商用利用モードでは追加フォントを登録できません")

        manim.register_font = reject_font_registration
