"""Core data models for video-autosplitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DetectionMethod(Enum):
    """Available split detection methods."""

    SILENCE = "silence"
    SCENE = "scene"
    BLACKFRAME = "blackframe"
    INTERVAL = "interval"


class Preset(Enum):
    """Content-type presets with tuned defaults."""

    PODCAST = "podcast"
    VLOG = "vlog"
    LECTURE = "lecture"
    SURVEILLANCE = "surveillance"
    MUSIC = "music"


PRESET_CONFIGS: dict[Preset, dict] = {
    Preset.PODCAST: {
        "method": DetectionMethod.SILENCE,
        "noise_db": -35,
        "min_silence": 2.0,
        "min_segment": 30.0,
    },
    Preset.VLOG: {
        "method": DetectionMethod.SCENE,
        "threshold": 27.0,
        "min_segment": 5.0,
    },
    Preset.LECTURE: {
        "method": DetectionMethod.SILENCE,
        "noise_db": -40,
        "min_silence": 3.0,
        "min_segment": 60.0,
    },
    Preset.SURVEILLANCE: {
        "method": DetectionMethod.SCENE,
        "threshold": 30.0,
        "min_segment": 10.0,
    },
    Preset.MUSIC: {
        "method": DetectionMethod.SILENCE,
        "noise_db": -50,
        "min_silence": 1.0,
        "min_segment": 15.0,
    },
}


@dataclass
class SplitPoint:
    """A detected point where a video should be split."""

    start: float  # seconds
    end: float  # seconds
    method: DetectionMethod
    confidence: float = 1.0  # 0.0 - 1.0
    label: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __repr__(self) -> str:
        return (
            f"SplitPoint({self._fmt(self.start)} → {self._fmt(self.end)}, "
            f"{self.method.value}, conf={self.confidence:.2f})"
        )

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class VideoInfo:
    """Metadata about the input video."""

    path: Path
    duration: float  # seconds
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    size_bytes: int = 0

    @property
    def duration_fmt(self) -> str:
        return SplitPoint._fmt(self.duration)


@dataclass
class SplitResult:
    """Result of a split operation."""

    input_file: Path
    output_files: list[Path] = field(default_factory=list)
    split_points: list[SplitPoint] = field(default_factory=list)
    method: DetectionMethod = DetectionMethod.SILENCE
    elapsed_seconds: float = 0.0
