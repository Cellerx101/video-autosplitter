"""Combined multi-method detection — runs multiple detectors and scores by agreement.

Split points that are confirmed by multiple methods get higher confidence scores,
producing more reliable cuts than any single method alone.
"""

from __future__ import annotations

from pathlib import Path

from ..ffmpeg_utils import probe_video
from ..models import DetectionMethod, SplitPoint


class CombinedDetector:
    """Run multiple detection methods and merge results by proximity.

    When a silence gap and a scene change occur near the same timestamp,
    that's a high-confidence split point. This detector finds those agreements.

    Ideal for: any content where single-method detection produces noisy results.
    """

    def __init__(
        self,
        methods: list[str] | None = None,
        tolerance: float = 2.0,
        min_segment: float = 10.0,
        noise_db: float = -35,
        min_silence: float = 2.0,
        threshold: float = 27.0,
    ):
        """
        Args:
            methods: List of methods to combine. Default: ["silence", "scene"].
                     Options: "silence", "scene", "blackframe"
            tolerance: Max seconds between two split points to consider them
                      the same cut. Default 2.0s.
            min_segment: Minimum segment duration in seconds.
            noise_db: Silence detection noise threshold.
            min_silence: Minimum silence duration for silence detector.
            threshold: Scene detection threshold.
        """
        self.methods = methods or ["silence", "scene"]
        self.tolerance = tolerance
        self.min_segment = min_segment
        self.noise_db = noise_db
        self.min_silence = min_silence
        self.threshold = threshold

    def detect(self, path: Path) -> list[SplitPoint]:
        """Run all specified detectors, then merge and score results."""
        info = probe_video(path)

        # Collect cut points from each method
        all_cuts: list[tuple[float, str]] = []  # (timestamp, method_name)

        for method in self.methods:
            cuts = self._run_method(method, path)
            for sp in cuts:
                # Use the start time of each segment (except first) as a cut point
                if sp.start > 0.1:
                    all_cuts.append((sp.start, method))

        if not all_cuts:
            return [
                SplitPoint(
                    start=0.0,
                    end=info.duration,
                    method=DetectionMethod.SILENCE,
                    confidence=1.0,
                    label="full",
                )
            ]

        # Sort all cuts by timestamp
        all_cuts.sort(key=lambda x: x[0])

        # Merge nearby cuts within tolerance window
        merged_cuts = self._merge_cuts(all_cuts)

        # Build segments from merged cut points
        cut_times = [0.0] + [c["time"] for c in merged_cuts] + [info.duration]
        segments: list[SplitPoint] = []

        for i in range(len(cut_times) - 1):
            start = cut_times[i]
            end = cut_times[i + 1]
            duration = end - start

            if duration < self.min_segment and segments:
                # Merge short segment with previous
                segments[-1].end = end
                continue

            # Confidence based on how many methods agreed at this cut point
            if i < len(merged_cuts):
                agreement = merged_cuts[i]["count"]
                total_methods = len(self.methods)
                confidence = min(1.0, agreement / total_methods)
            else:
                confidence = 0.5

            segments.append(
                SplitPoint(
                    start=start,
                    end=end,
                    method=DetectionMethod.SILENCE,  # combined
                    confidence=round(confidence, 2),
                    label=f"part_{len(segments) + 1:03d}",
                )
            )

        # Handle last segment being too short
        if len(segments) > 1 and segments[-1].duration < self.min_segment:
            segments[-2].end = segments[-1].end
            segments.pop()

        return segments

    def _run_method(self, method: str, path: Path) -> list[SplitPoint]:
        """Run a single detection method and return its split points."""
        if method == "silence":
            from .silence import SilenceDetector

            detector = SilenceDetector(
                noise_db=self.noise_db,
                min_silence=self.min_silence,
                min_segment=1.0,  # Use small min_segment to get all candidates
            )
            return detector.detect(path)

        elif method == "scene":
            from .scene import SceneDetector

            detector = SceneDetector(
                threshold=self.threshold,
                min_segment=1.0,
            )
            return detector.detect(path)

        elif method == "blackframe":
            from .blackframe import BlackFrameDetector

            detector = BlackFrameDetector(
                min_segment=1.0,
            )
            return detector.detect(path)

        else:
            raise ValueError(f"Unknown method: {method}. Use: silence, scene, blackframe")

    def _merge_cuts(
        self, cuts: list[tuple[float, str]]
    ) -> list[dict]:
        """Merge cut points that fall within the tolerance window.

        Returns list of dicts with:
            time: averaged timestamp of the merged cluster
            count: number of methods that agreed
            methods: list of method names that contributed
        """
        if not cuts:
            return []

        clusters: list[dict] = []
        current_cluster: list[tuple[float, str]] = [cuts[0]]

        for i in range(1, len(cuts)):
            timestamp, method = cuts[i]
            cluster_avg = sum(t for t, _ in current_cluster) / len(current_cluster)

            if timestamp - cluster_avg <= self.tolerance:
                current_cluster.append(cuts[i])
            else:
                # Finalize current cluster
                clusters.append(self._finalize_cluster(current_cluster))
                current_cluster = [cuts[i]]

        # Don't forget last cluster
        clusters.append(self._finalize_cluster(current_cluster))

        return clusters

    @staticmethod
    def _finalize_cluster(cluster: list[tuple[float, str]]) -> dict:
        """Convert a cluster of nearby cuts into a single merged cut point."""
        times = [t for t, _ in cluster]
        methods = list({m for _, m in cluster})  # unique methods
        return {
            "time": sum(times) / len(times),  # average timestamp
            "count": len(methods),  # number of distinct methods that agreed
            "methods": methods,
        }
