"""Tests for video-autosplitter."""

import pytest
from pathlib import Path

from autosplitter.models import SplitPoint, DetectionMethod, Preset, PRESET_CONFIGS, VideoInfo
from autosplitter.detectors.interval import IntervalDetector
from autosplitter.export import export_youtube_chapters, export_edl


class TestSplitPoint:
    def test_duration(self):
        sp = SplitPoint(start=10.0, end=25.0, method=DetectionMethod.SILENCE)
        assert sp.duration == 15.0

    def test_format_time(self):
        assert SplitPoint._fmt(3661) == "01:01:01"
        assert SplitPoint._fmt(0) == "00:00:00"
        assert SplitPoint._fmt(90) == "00:01:30"

    def test_repr(self):
        sp = SplitPoint(start=0, end=60, method=DetectionMethod.INTERVAL, confidence=1.0)
        r = repr(sp)
        assert "INTERVAL" in r or "interval" in r


class TestVideoInfo:
    def test_duration_fmt(self):
        vi = VideoInfo(path=Path("test.mp4"), duration=7261)
        assert vi.duration_fmt == "02:01:01"


class TestPresets:
    def test_all_presets_exist(self):
        for preset in Preset:
            assert preset in PRESET_CONFIGS

    def test_preset_has_method(self):
        for preset, config in PRESET_CONFIGS.items():
            assert "method" in config
            assert isinstance(config["method"], DetectionMethod)


class TestIntervalDetector:
    """IntervalDetector doesn't need FFmpeg — we can mock probe_video."""

    def test_basic_interval(self, monkeypatch):
        from autosplitter.detectors import interval as interval_mod

        # Mock probe_video to return a fake 5-minute video
        fake_info = VideoInfo(path=Path("test.mp4"), duration=300.0)
        monkeypatch.setattr(interval_mod, "probe_video", lambda p: fake_info)

        detector = IntervalDetector(interval=60.0)
        points = detector.detect(Path("test.mp4"))

        assert len(points) == 5
        assert points[0].start == 0.0
        assert points[0].end == 60.0
        assert points[-1].end == 300.0

    def test_short_video(self, monkeypatch):
        from autosplitter.detectors import interval as interval_mod

        fake_info = VideoInfo(path=Path("test.mp4"), duration=30.0)
        monkeypatch.setattr(interval_mod, "probe_video", lambda p: fake_info)

        detector = IntervalDetector(interval=60.0)
        points = detector.detect(Path("test.mp4"))

        assert len(points) == 1
        assert points[0].duration == 30.0


class TestExport:
    def test_youtube_chapters(self, tmp_path):
        points = [
            SplitPoint(start=0, end=60, method=DetectionMethod.SILENCE, label="Intro"),
            SplitPoint(start=60, end=180, method=DetectionMethod.SILENCE, label="Main"),
            SplitPoint(start=180, end=300, method=DetectionMethod.SILENCE, label="Outro"),
        ]
        out = export_youtube_chapters(points, tmp_path / "chapters.txt")
        text = out.read_text()
        assert "0:00 Intro" in text
        assert "1:00 Main" in text
        assert "3:00 Outro" in text

    def test_edl_export(self, tmp_path):
        points = [
            SplitPoint(start=0, end=30, method=DetectionMethod.SCENE, label="scene_001"),
        ]
        out = export_edl(points, tmp_path / "test.edl")
        text = out.read_text()
        assert "TITLE" in text
        assert "scene_001" in text
