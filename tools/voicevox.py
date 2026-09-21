#!/usr/bin/env python3
"""Generate a WAV narration file with a local VOICEVOX Engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def post_json(url: str, payload: bytes = b"") -> bytes:
    headers = {"Content-Type": "application/json"} if payload else {}
    request = Request(url, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=60) as response:
        return response.read()


def synthesize(text: str, speaker: int, base_url: str) -> bytes:
    endpoint = base_url.rstrip("/")
    query = urlencode({"text": text, "speaker": speaker})
    audio_query = post_json(f"{endpoint}/audio_query?{query}")
    return post_json(
        f"{endpoint}/synthesis?speaker={speaker}",
        json.dumps(json.loads(audio_query)).encode("utf-8"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VOICEVOX Engine で WAV を生成します")
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", help="読み上げる文章")
    text_group.add_argument("--text-file", type=Path, help="読み上げる文章を含む UTF-8 テキストファイル")
    parser.add_argument("--output", type=Path, required=True, help="出力 WAV パス")
    parser.add_argument("--speaker", type=int, default=3, help="VOICEVOX の話者 ID（既定値: 3）")
    parser.add_argument("--base-url", default="http://127.0.0.1:50021", help="VOICEVOX Engine の URL")
    args = parser.parse_args(argv)

    text = args.text if args.text is not None else args.text_file.read_text(encoding="utf-8")
    if not text.strip():
        parser.error("読み上げる文章は空にできません")
    try:
        wav = synthesize(text, args.speaker, args.base_url)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"VOICEVOX Engine との通信に失敗しました: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(wav)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
