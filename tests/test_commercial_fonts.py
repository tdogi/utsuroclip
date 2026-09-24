from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from utsuroclip.commercial_fonts import (
    CommercialFontError, commercial_font_environment, font_codepoints,
    validate_scene_sources,
)
from utsuroclip.font_guard import install_if_manim, validate_text


class CommercialFontTests(unittest.TestCase):
    def test_missing_math_font_fails_instead_of_using_fc_match_fallback(self) -> None:
        with TemporaryDirectory() as temp, patch(
            "utsuroclip.commercial_fonts.installed_fonts",
            return_value={"Noto Sans CJK JP": {Path(temp) / "sans.ttc"}},
        ):
            with self.assertRaisesRegex(CommercialFontError, "Noto Sans Math"):
                with commercial_font_environment():
                    pass

    def test_environment_contains_only_approved_font_files(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            sans, math = root / "sans.ttc", root / "math.ttf"
            sans.touch()
            math.touch()
            with patch("utsuroclip.commercial_fonts.installed_fonts", return_value={
                "Noto Sans CJK JP": {sans}, "Noto Sans Math": {math},
            }), patch("utsuroclip.commercial_fonts.font_codepoints", return_value={65, 66}):
                with commercial_font_environment() as env:
                    config = Path(env["FONTCONFIG_FILE"])
                    self.assertTrue(config.is_file())
                    self.assertIn("font-0", {p.stem for p in (config.parent / "fonts").iterdir()})
                    self.assertIn("sitecustomize.py", [p.name for p in config.parent.iterdir()])
                    self.assertIn("src", env["PYTHONPATH"])
                self.assertFalse(config.exists())

    def test_font_codepoints_parses_ranges(self) -> None:
        with patch("utsuroclip.commercial_fonts.subprocess.run", return_value=subprocess.CompletedProcess(
            [], 0, "41-43 2200\n", ""
        )):
            self.assertEqual(font_codepoints({Path("font.ttf")}), {65, 66, 67, 0x2200})

    def test_scene_audit_rejects_tex_and_unapproved_font(self) -> None:
        with TemporaryDirectory() as temp:
            scene = Path(temp) / "scene_001.py"
            scene.write_text('MathTex("x")', encoding="utf-8")
            with self.assertRaisesRegex(CommercialFontError, "MathTex"):
                validate_scene_sources(Path(temp))
            scene.write_text('Text("x", font="DejaVu Sans")', encoding="utf-8")
            with self.assertRaisesRegex(CommercialFontError, "DejaVu Sans"):
                validate_scene_sources(Path(temp))
            scene.write_text('Text("x", font="Noto Sans Math")', encoding="utf-8")
            validate_scene_sources(Path(temp))
            scene.write_text('register_font("custom.ttf")', encoding="utf-8")
            with self.assertRaisesRegex(CommercialFontError, "register_font"):
                validate_scene_sources(Path(temp))

    def test_guard_rejects_unsupported_glyphs(self) -> None:
        validate_text("A\n\t", {65})
        with self.assertRaisesRegex(RuntimeError, r"U\+2200"):
            validate_text("A∀", {65})

    def test_guard_checks_manim_text_and_rejects_tex(self) -> None:
        class Text:
            def __init__(self, text, **kwargs):
                self.text = text
                self.font = kwargs["font"]

        class MarkupText(Text):
            pass

        class Tex:
            def __init__(self, *args, **kwargs):
                pass

        class MathTex(Tex):
            pass

        fake_manim = types.SimpleNamespace(Text=Text, MarkupText=MarkupText, Tex=Tex, MathTex=MathTex)
        with TemporaryDirectory() as temp:
            charset = Path(temp) / "charset.json"
            charset.write_text("[65, 66]", encoding="utf-8")
            with patch.dict(sys.modules, {"manim": fake_manim}), patch.dict(
                "os.environ", {
                    "UTSUROCLIP_COMMERCIAL_CHARSET": str(charset),
                    "UTSUROCLIP_COMMERCIAL_FAMILIES": '["Noto Sans CJK JP", "Noto Sans Math"]',
                }
            ), patch.object(sys, "argv", ["/bin/manim"]):
                install_if_manim()
                self.assertEqual(Text("AB").font, "Noto Sans CJK JP")
                with self.assertRaisesRegex(RuntimeError, "許可されていない"):
                    Text("A", font="DejaVu Sans")
                with self.assertRaisesRegex(RuntimeError, "ない文字"):
                    Text("C")
                with self.assertRaisesRegex(RuntimeError, "必要なフォント"):
                    Text("A", font="Noto Serif CJK JP")
                with self.assertRaisesRegex(RuntimeError, "部分指定フォント"):
                    Text("A", t2f={"A": "DejaVu Sans"})
                with self.assertRaisesRegex(RuntimeError, "font_desc"):
                    MarkupText('<span font_desc="DejaVu Sans">A</span>')
                with self.assertRaisesRegex(RuntimeError, "Tex / MathTex"):
                    MathTex("A")
