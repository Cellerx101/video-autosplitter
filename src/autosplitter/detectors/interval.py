"""Fixed-interval split detection."""

from __future__ import annotations

from pathlib import Path

from ..ffmpeg_utils import probe_video
from ..models import DetectionMethod, SplitPoint


class IntervalDetector:
    """Split video at fixed time intervals.

    Ideal for: batch processing, creating clips of uniform length,
    splitting long recordings into manageable chunks.
    """

    def __init__(self, interval: float = 60.0):
        """
        Args:
            interval: Split interval in seconds. Default 60s.
        """
        self.interval = interval

    def detect(self, path: Path) -> list[SplitPoint]:
        """Generate split points at fixed intervals."""
        info = probe_video(path)
        segments: list[SplitPoint] = []

        current = 0.0
        i = 1
        while current < info.duration:
            end = min(current + self.interval, info.duration)
            segments.append(
                SplitPoint(
                    start=current,
                    end=end,
                    method=DetectionMethod.INTERVAL,
                    confidence=1.0,
                    label=f"part_{i:03d}",
                )
            )
            current = end
            i += 1

        return segments
