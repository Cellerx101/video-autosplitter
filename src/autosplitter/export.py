"""Export split points to various formats."""

from __future__ import annotations

from pathlib import Path

from .models import SplitPoint


def export_edl(split_points: list[SplitPoint], output_path: Path) -> Path:
    """Export split points as an Edit Decision List (EDL).

    Compatible with DaVinci Resolve, Premiere Pro, and other NLEs.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["TITLE: Auto-Split EDL", ""]
    for i, sp in enumerate(split_points, 1):
        # EDL format: ### event, reel, track, transition, src_in, src_out, rec_in, rec_out
        lines.append(
            f"{i:03d}  001  V  C  "
            f"{_tc(sp.start)} {_tc(sp.end)} "
            f"{_tc(sp.start)} {_tc(sp.end)}"
        )
        if sp.label:
            lines.append(f"* COMMENT: {sp.label}")
        lines.append("")

    output_path.write_text("\n".join(lines))
    return output_path


def export_youtube_chapters(split_points: list[SplitPoint], output_path: Path) -> Path:
    """Export split points as YouTube chapter timestamps.

    Format: 00:00 Chapter Title
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for sp in split_points:
        m, s = divmod(int(sp.start), 60)
        h, m = divmod(m, 60)
        if h > 0:
            ts = f"{h}:{m:02d}:{s:02d}"
        else:
            ts = f"{m}:{s:02d}"
        label = sp.label or "Untitled"
        lines.append(f"{ts} {label}")

    output_path.write_text("\n".join(lines))
    return output_path


def export_ffconcat(
    split_points: list[SplitPoint],
    input_path: Path,
    output_path: Path,
) -> Path:
    """Export as ffconcat demuxer file for re-joining segments.

    Can be used with: ffmpeg -f concat -i concat.txt -c copy output.mp4
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["ffconcat version 1.0", ""]
    stem = input_path.stem
    suffix = input_path.suffix

    for sp in split_points:
        label = sp.label or "part"
        filename = f"{stem}_{label}{suffix}"
        lines.append(f"file '{filename}'")

    output_path.write_text("\n".join(lines))
    return output_path


def _tc(seconds: float) -> str:
    """Convert seconds to SMPTE-ish timecode HH:MM:SS:FF (assuming 30fps)."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    f = int((seconds - int(seconds)) * 30)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
