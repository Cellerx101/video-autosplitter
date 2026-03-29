"""FFmpeg wrapper utilities — subprocess only, zero extra dependencies."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from .models import SplitPoint, VideoInfo


def check_ffmpeg() -> None:
    """Verify ffmpeg and ffprobe are available on PATH."""
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError(
                f"'{tool}' not found on PATH. Install FFmpeg: https://ffmpeg.org/download.html"
            )


def probe_video(path: Path) -> VideoInfo:
    """Extract video metadata using ffprobe."""
    check_ffmpeg()
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    size_bytes = int(fmt.get("size", 0))

    # Find video stream
    width = height = 0
    fps = 0.0
    codec = ""
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            codec = stream.get("codec_name", "")
            # Parse fps from r_frame_rate (e.g. "30000/1001")
            r_fps = stream.get("r_frame_rate", "0/1")
            if "/" in r_fps:
                num, den = r_fps.split("/")
                fps = float(num) / float(den) if float(den) else 0.0
            else:
                fps = float(r_fps)
            break

    return VideoInfo(
        path=path,
        duration=duration,
        width=width,
        height=height,
        fps=round(fps, 3),
        codec=codec,
        size_bytes=size_bytes,
    )


def detect_silence(
    path: Path,
    noise_db: float = -35,
    min_silence: float = 2.0,
) -> list[tuple[float, float]]:
    """Detect silence periods using FFmpeg silencedetect filter.

    Returns list of (start, end) tuples for each silence period.
    """
    check_ffmpeg()
    cmd = [
        "ffmpeg",
        "-i", str(path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}",
        "-vn",  # skip video decoding — much faster
        "-f", "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence_start and silence_end from stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", stderr)]

    # Pair them up — sometimes the last silence has no end
    pairs = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else start + min_silence
        pairs.append((start, end))

    return pairs


def detect_black_frames(
    path: Path,
    threshold: float = 0.1,
    min_duration: float = 0.5,
) -> list[tuple[float, float]]:
    """Detect black frame periods using FFmpeg blackdetect filter.

    Returns list of (start, end) tuples.
    """
    check_ffmpeg()
    cmd = [
        "ffmpeg",
        "-i", str(path),
        "-vf", f"blackdetect=d={min_duration}:pix_th={threshold}",
        "-an",
        "-f", "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    starts = [float(m) for m in re.findall(r"black_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"black_end:\s*([\d.]+)", stderr)]

    pairs = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else start + min_duration
        pairs.append((start, end))

    return pairs


def split_video(
    input_path: Path,
    split_points: list[SplitPoint],
    output_dir: Path,
    reencode: bool = False,
    output_format: str | None = None,
) -> list[Path]:
    """Split a video file at the given split points.

    Uses stream copy by default (fast, keyframe-aligned).
    Set reencode=True for frame-accurate cuts.
    """
    check_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = f".{output_format}" if output_format else input_path.suffix
    stem = input_path.stem
    output_files: list[Path] = []

    for i, sp in enumerate(split_points, 1):
        label = sp.label or f"part_{i:03d}"
        out_path = output_dir / f"{stem}_{label}{suffix}"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(sp.start),
            "-i", str(input_path),
            "-t", str(sp.duration),
        ]

        if reencode:
            cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"]
        else:
            cmd += ["-c", "copy"]

        # Avoid negative timestamps
        cmd += ["-avoid_negative_ts", "make_zero"]
        cmd.append(str(out_path))

        subprocess.run(cmd, capture_output=True, check=True)
        output_files.append(out_path)

    return output_files
