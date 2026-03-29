"""Scene-change-based split detection using PySceneDetect.

Requires optional dependency: pip install video-autosplitter[scene]
"""

from __future__ import annotations

from pathlib import Path

from ..models import DetectionMethod, SplitPoint


class SceneDetector:
    """Detect split points at visual scene changes.

    Ideal for: vlogs, multi-camera shoots, surveillance footage.
    Requires: pip install video-autosplitter[scene]
    """

    def __init__(
        self,
        threshold: float = 27.0,
        min_segment: float = 5.0,
    ):
        self.threshold = threshold
        self.min_segment = min_segment

    def detect(self, path: Path) -> list[SplitPoint]:
        """Find split points at scene boundaries."""
        try:
            from scenedetect import SceneManager, open_video
            from scenedetect.detectors import AdaptiveDetector
        except ImportError:
            raise ImportError(
                "Scene detection requires PySceneDetect. "
                "Install with: pip install video-autosplitter[scene]"
            )

        video = open_video(str(path))
        scene_manager = SceneManager()
        scene_manager.add_detector(
            AdaptiveDetector(
                adaptive_threshold=self.threshold,
                min_scene_len=int(self.min_segment * video.frame_rate),
            )
        )
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()

        if not scene_list:
            # No scenes detected — return full video
            from ..ffmpeg_utils import probe_video

            info = probe_video(path)
            return [
                SplitPoint(
                    start=0.0,
                    end=info.duration,
                    method=DetectionMethod.SCENE,
                    label="full",
                )
            ]

        segments: list[SplitPoint] = []
        for i, (start_time, end_time) in enumerate(scene_list, 1):
            segments.append(
                SplitPoint(
                    start=start_time.get_seconds(),
                    end=end_time.get_seconds(),
                    method=DetectionMethod.SCENE,
                    confidence=0.85,
                    label=f"scene_{i:03d}",
                )
            )

        return segments
