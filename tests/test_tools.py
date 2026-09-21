from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[1]


def load_tool(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "tools" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


voicevox = load_tool("voicevox_tool", "voicevox.py")
ffmpeg = load_tool("ffmpeg_tool", "ffmpeg.py")


class ToolTests(unittest.TestCase):
    def test_voicevox_calls_query_then_synthesis(self) -> None:
        with patch.object(voicevox, "post_json", side_effect=[b'{"speedScale": 1}', b"WAV"]) as post:
            result = voicevox.synthesize("こんにちは", 3, "http://localhost:50021/")

        self.assertEqual(result, b"WAV")
        self.assertIn("/audio_query?", post.call_args_list[0].args[0])
        self.assertEqual(post.call_args_list[1].args[0], "http://localhost:50021/synthesis?speaker=3")

    def test_voicevox_uses_kasukabe_tsumugi_by_default(self) -> None:
        with TemporaryDirectory() as temp:
            output = Path(temp) / "scene.wav"
            with patch.object(voicevox, "synthesize", return_value=b"WAV") as synthesize:
                result = voicevox.main(["--text", "こんにちは", "--output", str(output)])

        self.assertEqual(result, 0)
        self.assertEqual(synthesize.call_args.args[1], 8)

    def test_voicevox_uses_selected_speaker(self) -> None:
        with TemporaryDirectory() as temp:
            output = Path(temp) / "scene.wav"
            with patch.object(voicevox, "synthesize", return_value=b"WAV") as synthesize:
                result = voicevox.main([
                    "--text", "こんにちは", "--output", str(output), "--speaker", "四国めたん"
                ])

        self.assertEqual(result, 0)
        self.assertEqual(synthesize.call_args.args[1], 2)

    def test_ffmpeg_mux_builds_audio_video_command(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            video, audio = root / "scene.mp4", root / "scene.wav"
            video.touch()
            audio.touch()
            with patch.object(ffmpeg, "require_ffmpeg", return_value=True), patch.object(ffmpeg, "run", return_value=0) as run:
                result = ffmpeg.main(["mux", "--video", str(video), "--audio", str(audio), "--output", str(root / "out.mp4")])

        self.assertEqual(result, 0)
        command = run.call_args.args[0]
        self.assertIn("-shortest", command)
        self.assertIn("-c:a", command)

    def test_ffmpeg_concat_removes_temporary_manifest(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "one.mp4", root / "two.mp4"
            first.touch()
            second.touch()
            with patch.object(ffmpeg, "require_ffmpeg", return_value=True), patch.object(ffmpeg, "run", return_value=0) as run:
                result = ffmpeg.main(["concat", str(first), str(second), "--output", str(root / "out.mp4")])

        self.assertEqual(result, 0)
        self.assertIn("concat", run.call_args.args[0])
