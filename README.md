VIDEO-AUTOSPLITTER  *S V A*

**Automatically split videos using silence detection, scene changes, black frames, or fixed intervals.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

After discovering what ffmpeg was and seeing its ulttilty that the libraries just freely give us, I was motivated to try and create soemthing I thought would be helpful to the creators of all types.  Video-Autosplitter is simple and solves the issues of video formating and clipping in seconds.  Below is what i have managed to put togehter with the help of Claude by Anthropic.  



> One CLI tool. Four detection methods. Zero re-encoding by default.

Most video splitting tools do one thing — silence detection OR scene detection OR fixed intervals.  The Autosplit tool combines all four methods into a single CLI with content-type presets, dry-run previews, and multi-format export (EDL, YouTube chapters, ffconcat).

 Features

- **Silence detection** — Split at audio gaps. Perfect for podcasts, lectures, interviews.
- **Scene detection** — Split at visual cuts using [PySceneDetect](https://www.scenedetect.com/)'s adaptive algorithm.
- **Black frame detection** — Split at fade-to-black transitions. Ideal for TV recordings and presentations.
- **Fixed intervals** — Split every N seconds. Simple batch processing.
- **Content presets** — `--preset podcast`, `--preset vlog`, `--preset lecture` auto-configure thresholds based on Your input 
- **Dry-run mode** — Preview split points without writing files.
- **Export formats** — EDL (Premiere/Resolve), YouTube chapter timestamps, ffconcat.
- **JSON output** — Pipe results to other tools with `--json-output`.
- **Stream copy by default** — No re-encoding, near-instant splitting. Use `--reencode` for frame-accurate cuts.

## Installation

### From source (recommended for now)

```bash
git clone https://github.com/Cellerx101/video-autosplitter.git
cd video-autosplitter
pip install -e .
```

### With scene detection support

```bash
pip install -e ".[scene]"
```

### Requirements

- **Python 3.10+**
- **FFmpeg** on your PATH — [download here](https://ffmpeg.org/download.html)

## Quick Start

```bash
# Split a podcast at silence gaps
autosplit split recording.mp4

# Split a vlog at scene changes
autosplit split video.mp4 -m scene

# Split at black frames (TV recordings)
autosplit split capture.mp4 -m blackframe

# Split every 2 minutes
autosplit split long_video.mp4 -m interval --interval 120

# Use a content preset
autosplit split lecture.mp4 --preset lecture

# Preview splits without writing files
autosplit split video.mp4 --dry-run

# Export as YouTube chapter timestamps
autosplit split video.mp4 --dry-run --export chapters

# Get JSON output for scripting
autosplit split video.mp4 --dry-run --json-output
```

## DETECTION METHODS (-m)

### Silence detection (default)
Splits at audio gaps. Best for: podcasts, lectures, interviews.
```bash
autosplit split video.mp4 -m silence

### Scene detection
Splits at visual changes. Best for: vlogs, trailers, compilations, anime.
```bash
autosplit split video.mp4 -m scene
```
### Black frame detection
Splits at fade-to-black transitions. Best for: TV recordings, presentations.
```bash
autosplit split video.mp4 -m blackframe
```
### Fixed interval
Splits every N seconds. Best for: batch processing, uniform clips.
```bash
autosplit split video.mp4 -m interval --interval 60
```
### Combined (multi-method)
Runs multiple methods and scores by agreement. Best for: highest accuracy.
```bash
autosplit split video.mp4 -m combined
```

### Content Presets

Presets auto-configure detection thresholds for specific content types:

```bash
autosplit split file.mp4 --preset podcast    # Silence, -35dB, 2s gaps, 30s min
autosplit split file.mp4 --preset vlog       # Scene, threshold 27, 5s min
autosplit split file.mp4 --preset lecture     # Silence, -40dB, 3s gaps, 60s min
autosplit split file.mp4 --preset surveillance # Scene, threshold 30, 10s min
autosplit split file.mp4 --preset music       # Silence, -50dB, 1s gaps, 15s min
```

### Tuning Parameters

```bash
# Silence detection
autosplit split file.mp4 -m silence \
    --noise-db -40 \         # Noise floor (lower = more sensitive)
    --min-silence 3.0 \      # Min silence duration to trigger split
    --min-segment 60.0       # Don't create segments shorter than this

# Scene detection
autosplit split file.mp4 -m scene \
    --threshold 20.0 \       # Lower = more sensitive (more splits)
    --min-segment 3.0        # Min scene length in seconds

# Fixed interval
autosplit split file.mp4 -m interval --interval 90  # Every 90 seconds
```

### Export Formats

```bash
# EDL for Premiere Pro / DaVinci Resolve
autosplit split video.mp4 --export edl

# YouTube chapter timestamps
autosplit split video.mp4 --dry-run --export chapters

# ffconcat for re-joining with FFmpeg
autosplit split video.mp4 --export ffconcat
```

### Video Info

```bash
autosplit info video.mp4
```

### Python API

```python
from autosplitter import run_split, DetectionMethod, Preset

# Basic split
result = run_split("video.mp4", method=DetectionMethod.SILENCE)

# With preset
result = run_split("lecture.mp4", preset=Preset.LECTURE)

# Dry run — just get split points
result = run_split("video.mp4", dry_run=True)
for sp in result.split_points:
    print(f"{sp.label}: {sp.start:.1f}s → {sp.end:.1f}s ({sp.duration:.1f}s)")
```

## How It Works

```
┌─────────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐
│  Input   │────▶│  Detector │────▶│  Split   │────▶│ Output  │
│  Video   │     │  Engine   │     │  Points  │     │  Files  │
└─────────┘     └───────────┘     └──────────┘     └─────────┘
                      │
          ┌───────────┼───────────┐──────────┐
          │           │           │          │
     ┌────▼───┐ ┌─────▼────┐ ┌───▼────┐ ┌───▼─────┐
     │Silence │ │  Scene   │ │ Black  │ │Interval │
     │Detect  │ │  Detect  │ │ Frame  │ │         │
     └────────┘ └──────────┘ └────────┘ └─────────┘
```

1. **Detection** — The selected detector analyzes the video and returns a list of `SplitPoint` objects with timestamps.
2. **Merging** — Short segments below `min_segment` are merged with neighbors.
3. **Splitting** — FFmpeg splits the video at each point using stream copy (fast) or re-encoding (accurate).
4. **Export** — Optionally exports split points to EDL, chapter timestamps, or ffconcat.

## Project Structure

```
video-autosplitter/
├── src/autosplitter/
│   ├── __init__.py          # Public API
│   ├── cli.py               # Click CLI
│   ├── models.py            # SplitPoint, VideoInfo, presets
│   ├── splitter.py          # Core engine
│   ├── ffmpeg_utils.py      # FFmpeg subprocess wrappers
│   ├── export.py            # EDL, chapters, ffconcat export
│   └── detectors/
│       ├── silence.py       # Audio silence detection
│       ├── scene.py         # Visual scene detection
│       ├── blackframe.py    # Black frame detection
│       └── interval.py      # Fixed interval splitting
├── tests/
│   └── test_core.py
├── pyproject.toml
├── LICENSE
└── README.md
```

## Contributing

Contributions welcome. Open an issue or PR.

```bash
# Dev setup
git clone https://github.com/Cellerx101/video-autosplitter.git
cd video-autosplitter
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

## License

[MIT](LICENSE) — do whatever you want with it.

---

Built by [CJ McMahon](https://github.com/Cellerx101)
