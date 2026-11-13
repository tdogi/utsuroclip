"""Find an explicitly stated target duration in a video overview."""

from __future__ import annotations

from pathlib import Path
import math
import re
import unicodedata


_TIME = re.compile(r"(?:(\d+(?:\.\d+)?)\s*分\s*(半|\d+\s*秒)?|(\d+(?:\.\d+)?)\s*秒)")
_RANGE = re.compile(r"(?:\s*(?:〜|~|から|-)\s*)")


def _seconds(match: re.Match[str]) -> float:
    if match.group(3) is not None:
        return float(match.group(3))
    minutes = float(match.group(1))
    remainder = match.group(2)
    if remainder == "半":
        return minutes * 60 + 30
    return minutes * 60 + (float(remainder[:-1].strip()) if remainder else 0)


def _first_duration(text: str) -> float | None:
    matches = [
        match for match in _TIME.finditer(text)
        if not re.match(r"\s*の\s*\d", text[match.end():])
    ]
    if not matches:
        return None
    first = matches[0]
    if len(matches) > 1 and _RANGE.fullmatch(text[first.end():matches[1].start()]):
        return (_seconds(first) + _seconds(matches[1])) / 2
    return _seconds(first)


def requested_duration(request: Path) -> float | None:
    """Return an explicit time, including one embedded in natural language.

    Ambiguous or absent times are left to the script-writing stage to infer.
    """
    content = unicodedata.normalize("NFKC", request.read_text(encoding="utf-8"))
    section = re.search(
        r"(?ms)^#{1,6}\s*動画時間\s*\n(.*?)(?=^#{1,6}\s|\Z)", content
    )
    if section is not None:
        seconds = _first_duration(section.group(1))
        if seconds is not None:
            return seconds
    for line in content.splitlines():
        if re.search(r"(?:動画時間|動画の長さ|目標尺|尺)\s*[:：]", line):
            seconds = _first_duration(line)
            if seconds is not None:
                return seconds
    for line in content.splitlines():
        standalone = re.fullmatch(
            r"\s*(?:約|およそ)?\s*" + _TIME.pattern +
            r"\s*(?:ほど|くらい|ぐらい|程度|前後)?\s*", line
        )
        contextual = re.search(
            r"(?:動画|尺|長さ|秒|分).*(?:ほど|くらい|ぐらい|程度|前後|以内|で|目標|希望|想定|まとめ|説明|紹介)",
            line,
        )
        if not standalone and not contextual:
            continue
        seconds = _first_duration(line)
        if seconds is not None:
            return seconds
    return None


def read_duration_record(path: Path) -> float | None:
    """Read the script stage's plain-number target in seconds."""
    try:
        seconds = float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return seconds if math.isfinite(seconds) and seconds > 0 else None
