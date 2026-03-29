"""Core splitter engine — ties detection and splitting together."""

from __future__ import annotations

import time
from pathlib import Path

from .detectors import (
    BlackFrameDetector,
    IntervalDetector,
    SceneDetector,
    SilenceDetector,
)
from .ffmpeg_utils import split_video
from .models import (
    PRESET_CONFIGS,
    DetectionMethod,
    Preset,
    SplitResult,
)


def get_detector(
    method: DetectionMethod,
    **kwargs,
) -> SilenceDetector | SceneDetector | BlackFrameDetector | IntervalDetector:
    """Factory for creating the right detector."""
    detectors = {
        DetectionMethod.SILENCE: SilenceDetector,
        DetectionMethod.SCENE: SceneDetector,
        DetectionMethod.BLACKFRAME: BlackFrameDetector,
        DetectionMethod.INTERVAL: IntervalDetector,
    }
    cls = detectors[method]

    # Filter kwargs to only those the detector accepts
    import inspect

    sig = inspect.signature(cls.__init__)
    valid_params = {k for k in sig.parameters if k != "self"}
    filtered = {k: v for k, v in kwargs.items() if k in valid_params}

    return cls(**filtered)


def run_split(
    input_path: str | Path,
    method: DetectionMethod = DetectionMethod.SILENCE,
    output_dir: str | Path | None = None,
    preset: Preset | None = None,
    dry_run: bool = False,
    reencode: bool = False,
    output_format: str | None = None,
    **kwargs,
) -> SplitResult:
    """Main entry point — detect split points and optionally split the file.

    Args:
        input_path: Path to input video file.
        method: Detection method to use.
        output_dir: Directory for output files. Defaults to ./output/.
        preset: Content-type preset (overrides method and params).
        dry_run: If True, detect splits but don't write files.
        reencode: If True, re-encode for frame-accurate cuts.
        output_format: Output file extension (e.g. "mp4", "mkv").
        **kwargs: Additional detector-specific parameters.

    Returns:
        SplitResult with detected split points and output file paths.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_dir is None:
        output_dir = input_path.parent / "output"
    output_dir = Path(output_dir)

    # Apply preset if given
    if preset is not None:
        config = PRESET_CONFIGS[preset]
        method = config.get("method", method)
        # Preset values are defaults; explicit kwargs override them
        merged = {**config, **kwargs}
        merged.pop("method", None)
        kwargs = merged

    t0 = time.time()

    # Detect
    detector = get_detector(method, **kwargs)
    split_points = detector.detect(input_path)

    result = SplitResult(
        input_file=input_path,
        split_points=split_points,
        method=method,
    )

    # Split (unless dry run)
    if not dry_run and len(split_points) > 0:
        result.output_files = split_video(
            input_path,
            split_points,
            output_dir,
            reencode=reencode,
            output_format=output_format,
        )

    result.elapsed_seconds = time.time() - t0
    return result
