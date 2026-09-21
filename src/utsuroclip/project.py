"""Project paths and workspace preparation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Paths owned by one UtsuroClip project."""

    root: Path

    @property
    def prompts(self) -> Path:
        return self.root / "prompts"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def logs(self) -> Path:
        return self.work / "logs"

    @property
    def output(self) -> Path:
        return self.root / "output"

    def prepare_workspace(self) -> None:
        """Create the documented generated-artifact directories if absent."""
        for directory in (
            self.work / "research",
            self.work / "script",
            self.work / "audio",
            self.work / "scenes",
            self.work / "rendered",
            self.logs,
            self.output,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def require_assets(self) -> None:
        """Reject execution from a directory that is not a UtsuroClip project."""
        required = [
            self.prompts / "research.md",
            self.prompts / "write-script.md",
            self.prompts / "generate-video.md",
        ]
        missing = [str(path.relative_to(self.root)) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "UtsuroClip のプロンプトが見つかりません: " + ", ".join(missing)
            )
