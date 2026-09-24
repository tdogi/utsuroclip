"""Project paths and workspace preparation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path


class ProjectStateError(RuntimeError):
    """Raised when a Codex run changes files outside its allowed artifacts."""


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

    @property
    def title_file(self) -> Path:
        return self.work / "script" / "title.txt"

    @property
    def final_video_record(self) -> Path:
        """One-line relative path of the video currently backed by ``work/``."""
        return self.logs / "final-video.txt"

    @property
    def speaker_record(self) -> Path:
        """Narration speaker used for the video currently backed by ``work/``."""
        return self.logs / "speaker.txt"

    @property
    def bgm_record(self) -> Path:
        """Relative path of the BGM retained for future revisions."""
        return self.logs / "bgm.txt"

    def intermediate_artifacts(self) -> list[Path]:
        """Return generated files that would be removed before a new run."""
        if not self.work.is_dir():
            return []
        return sorted(
            (
                path
                for path in self.work.rglob("*")
                if path.name != ".gitkeep" and (path.is_file() or path.is_symlink())
            ),
            key=lambda path: str(path),
        )

    def clean_intermediate_artifacts(self) -> None:
        """Remove generated files while retaining workspace directories and .gitkeep."""
        for path in self.intermediate_artifacts():
            path.unlink()

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
            self.prompts / "self-check-video.md",
        ]
        missing = [str(path.relative_to(self.root)) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "UtsuroClip のプロンプトが見つかりません: " + ", ".join(missing)
            )

    def require_revision_assets(self) -> None:
        """Reject revision when the retained production set is incomplete."""
        required = [
            self.prompts / "revise-video.md",
            self.prompts / "self-check-video.md",
            self.work / "script" / "script.md",
            self.final_video_record,
            self.speaker_record,
        ]
        missing = [str(path.relative_to(self.root)) for path in required if not path.is_file()]
        scene_sets = (
            (self.work / "audio", "scene_*.wav"),
            (self.work / "scenes", "scene_*.py"),
            (self.work / "rendered", "scene_*.mp4"),
        )
        for directory, pattern in scene_sets:
            if not any(directory.glob(pattern)):
                missing.append(f"{directory.relative_to(self.root)}/{pattern}")
        if missing:
            raise FileNotFoundError(
                "修正に必要な制作素材または記録が見つかりません: " + ", ".join(missing)
            )

    def tools_snapshot(self) -> dict[Path, str]:
        """Return a content-aware snapshot of the tools supplied by UtsuroClip."""
        tools = self.root / "tools"
        if not tools.is_dir():
            return {}
        snapshot: dict[Path, str] = {}
        for path in sorted(tools.rglob("*")):
            relative = path.relative_to(self.root)
            if path.is_dir():
                snapshot[relative] = "directory"
            elif path.is_symlink():
                snapshot[relative] = f"symlink:{path.readlink()}"
            elif path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                snapshot[relative] = f"file:{digest}"
        return snapshot

    def require_tools_unchanged(self, before: dict[Path, str]) -> None:
        """Reject a Codex run that changed supplied tools instead of making artifacts."""
        after = self.tools_snapshot()
        changed = sorted(set(before) | set(after))
        changed = [path for path in changed if before.get(path) != after.get(path)]
        if changed:
            names = ", ".join(str(path) for path in changed)
            raise ProjectStateError(
                "Codex が許可されていない tools/ の変更を行いました: " + names
            )
