"""video-autosplitter — Automatically split videos using multiple detection methods."""

__version__ = "0.1.0"

from .models import DetectionMethod, Preset, SplitPoint, SplitResult
from .splitter import run_split

__all__ = [
    "DetectionMethod",
    "Preset",
    "SplitPoint",
    "SplitResult",
    "run_split",
]
