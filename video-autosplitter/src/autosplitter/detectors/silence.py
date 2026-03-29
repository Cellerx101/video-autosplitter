"""Silence-based split detection using FFmpeg silencedetect."""

from __future__ import annotations

from pathlib import Path

from ..ffmpeg_utils import detect_silence, probe_video
from ..models import DetectionMethod, SplitPoint


class SilenceDetector:
    """Detect split points at silence gaps in audio.

    Ideal for: podcasts, lectures, interviews, audiobooks.
    """

    def __init__(
        self,
        noise_db: float = -35,
        min_silence: float = 2.0,
        min_segment: float = 30.0,
    ):
        self.noise_db = noise_db
        self.min_silence = min_silence
        self.min_segment = min_segment

    def detect(self, path: Path) -> list[SplitPoint]:
        """Find split points at silence boundaries.

        Splits occur at the midpoint of each detected silence period.
        Segments shorter than min_segment are merged with neighbors.
        """
        info = probe_video(path)
        silences = detect_silence(path, self.noise_db, self.min_silence)

        if not silences:
            # No silence found — return entire video as one segment
            return [
                SplitPoint(
                    start=0.0,
                    end=info.duration,
                    method=DetectionMethod.SILENCE,
                    label="full",
                )
            ]

        # Build split points: each segment runs from one silence midpoint to the next
        cut_points = [0.0]
        for start, end in silences:
            midpoint = (start + end) / 2
            cut_points.append(midpoint)
        cut_points.append(info.duration)

        # Build raw segments
        raw_segments: list[SplitPoint] = []
        for i in range(len(cut_points) - 1):
            seg_start = cut_points[i]
            seg_end = cut_points[i + 1]
            if seg_end - seg_start > 0.1:  # skip near-zero segments
                raw_segments.append(
                    SplitPoint(
                        start=seg_start,
                        end=seg_end,
                        method=DetectionMethod.SILENCE,
                        confidence=0.9,
                    )
                )

        # Merge short segments
        segments = self._merge_short(raw_segments)

        # Label segments
        for i, seg in enumerate(segments, 1):
            seg.label = f"part_{i:03d}"

        return segments

    def _merge_short(self, segments: list[SplitPoint]) -> list[SplitPoint]:
        """Merge segments shorter than min_segment with their neighbors."""
        if not segments:
            return segments

        merged: list[SplitPoint] = [segments[0]]
        for seg in segments[1:]:
            if merged[-1].duration < self.min_segment:
                # Extend previous segment
                merged[-1].end = seg.end
            else:
                merged.append(seg)

        # Check if the last segment is too short
        if len(merged) > 1 and merged[-1].duration < self.min_segment:
            merged[-2].end = merged[-1].end
            merged.pop()

        return merged
