"""Black-frame-based split detection using FFmpeg blackdetect."""

from __future__ import annotations

from pathlib import Path

from ..ffmpeg_utils import detect_black_frames, probe_video
from ..models import DetectionMethod, SplitPoint


class BlackFrameDetector:
    """Detect split points at black frame transitions.

    Ideal for: TV recordings, presentations with fade-to-black, DVR captures.
    """

    def __init__(
        self,
        threshold: float = 0.1,
        min_duration: float = 0.5,
        min_segment: float = 10.0,
    ):
        self.threshold = threshold
        self.min_duration = min_duration
        self.min_segment = min_segment

    def detect(self, path: Path) -> list[SplitPoint]:
        """Find split points at black frame boundaries."""
        info = probe_video(path)
        blacks = detect_black_frames(path, self.threshold, self.min_duration)

        if not blacks:
            return [
                SplitPoint(
                    start=0.0,
                    end=info.duration,
                    method=DetectionMethod.BLACKFRAME,
                    label="full",
                )
            ]

        # Split at the midpoint of each black period
        cut_points = [0.0]
        for start, end in blacks:
            midpoint = (start + end) / 2
            cut_points.append(midpoint)
        cut_points.append(info.duration)

        segments: list[SplitPoint] = []
        for i in range(len(cut_points) - 1):
            seg_start = cut_points[i]
            seg_end = cut_points[i + 1]
            duration = seg_end - seg_start

            if duration >= self.min_segment:
                segments.append(
                    SplitPoint(
                        start=seg_start,
                        end=seg_end,
                        method=DetectionMethod.BLACKFRAME,
                        confidence=0.8,
                        label=f"part_{len(segments) + 1:03d}",
                    )
                )
            elif segments:
                # Merge short segment with previous
                segments[-1].end = seg_end

        if not segments:
            return [
                SplitPoint(
                    start=0.0,
                    end=info.duration,
                    method=DetectionMethod.BLACKFRAME,
                    label="full",
                )
            ]

        return segments
