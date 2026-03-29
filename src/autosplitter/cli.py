"""Command-line interface for video-autosplitter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .export import export_edl, export_ffconcat, export_youtube_chapters
from .models import DetectionMethod, Preset
from .splitter import run_split

console = Console()

METHOD_CHOICES = click.Choice(["silence", "scene", "blackframe", "interval, "combined"])
PRESET_CHOICES = click.Choice(["podcast", "vlog", "lecture", "surveillance", "music"])


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="autosplit")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Video Auto-Splitter — Split videos by silence, scene, black frames, or intervals."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("-m", "--method", type=METHOD_CHOICES, default="silence", help="Detection method.")
@click.option("-p", "--preset", type=PRESET_CHOICES, default=None, help="Content preset.")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None, help="Output dir.")
@click.option("--dry-run", is_flag=True, help="Detect splits without writing files.")
@click.option("--reencode", is_flag=True, help="Re-encode for frame-accurate cuts.")
@click.option("--format", "output_format", default=None, help="Output format (mp4, mkv, etc).")
@click.option("--noise-db", type=float, default=-35, help="Silence noise threshold in dB.")
@click.option("--min-silence", type=float, default=2.0, help="Min silence duration (seconds).")
@click.option("--min-segment", type=float, default=30.0, help="Min segment duration (seconds).")
@click.option("--threshold", type=float, default=27.0, help="Scene detection threshold.")
@click.option("--interval", type=float, default=60.0, help="Fixed interval (seconds).")
@click.option("--json-output", is_flag=True, help="Output results as JSON.")
@click.option("--export", "export_fmt", type=click.Choice(["edl", "chapters", "ffconcat"]),
              default=None, help="Export split points to format.")
def split(
    input_file: Path,
    method: str,
    preset: str | None,
    output: Path | None,
    dry_run: bool,
    reencode: bool,
    output_format: str | None,
    noise_db: float,
    min_silence: float,
    min_segment: float,
    threshold: float,
    interval: float,
    json_output: bool,
    export_fmt: str | None,
) -> None:
    """Split a video file into segments."""
    detection_method = DetectionMethod(method)
    content_preset = Preset(preset) if preset else None

    kwargs = {
        "noise_db": noise_db,
        "min_silence": min_silence,
        "min_segment": min_segment,
        "threshold": threshold,
        "interval": interval,
    }

    if not json_output:
        console.print(f"\n[bold yellow]⚡ autosplit[/] v{__version__}")
        console.print(f"  Input:  [cyan]{input_file}[/]")
        console.print(f"  Method: [green]{method}[/]")
        if content_preset:
            console.print(f"  Preset: [magenta]{preset}[/]")
        if dry_run:
            console.print("  Mode:   [yellow]DRY RUN[/] (no files written)")
        console.print()

    try:
        with console.status("[bold green]Analyzing video...") if not json_output else _noop():
            result = run_split(
                input_path=input_file,
                method=detection_method,
                output_dir=output,
                preset=content_preset,
                dry_run=dry_run,
                reencode=reencode,
                output_format=output_format,
                **kwargs,
            )
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"error": str(e)}))
        else:
            console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

    # Export if requested
    if export_fmt and result.split_points:
        export_path = (output or input_file.parent) / f"{input_file.stem}_splits"
        if export_fmt == "edl":
            path = export_edl(result.split_points, export_path.with_suffix(".edl"))
        elif export_fmt == "chapters":
            path = export_youtube_chapters(result.split_points, export_path.with_suffix(".txt"))
        elif export_fmt == "ffconcat":
            path = export_ffconcat(result.split_points, input_file, export_path.with_suffix(".txt"))

        if not json_output:
            console.print(f"  Exported: [cyan]{path}[/]\n")

    if json_output:
        _print_json(result)
    else:
        _print_table(result, dry_run)


@main.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
def info(input_file: Path) -> None:
    """Show video file information."""
    from .ffmpeg_utils import probe_video

    vid = probe_video(input_file)
    console.print("\n[bold yellow]⚡ Video Info[/]")
    console.print(f"  File:     [cyan]{vid.path.name}[/]")
    console.print(f"  Duration: [green]{vid.duration_fmt}[/] ({vid.duration:.1f}s)")
    console.print(f"  Size:     {vid.size_bytes / 1_048_576:.1f} MB")
    console.print(f"  Codec:    {vid.codec}")
    console.print(f"  Resolution: {vid.width}x{vid.height}")
    console.print(f"  FPS:      {vid.fps}")
    console.print()


def _print_table(result, dry_run: bool) -> None:
    """Pretty-print split results as a rich table."""
    table = Table(title="Split Points", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Start", style="cyan")
    table.add_column("End", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("Label", style="yellow")

    for i, sp in enumerate(result.split_points, 1):
        table.add_row(
            str(i),
            sp._fmt(sp.start),
            sp._fmt(sp.end),
            f"{sp.duration:.1f}s",
            sp.label,
        )

    console.print(table)
    console.print(
        f"\n  [bold]{len(result.split_points)}[/] segments detected "
        f"in [green]{result.elapsed_seconds:.1f}s[/]"
    )

    if not dry_run and result.output_files:
        console.print(f"  Output: [cyan]{result.output_files[0].parent}[/]")
    console.print()


def _print_json(result) -> None:
    """Output results as machine-readable JSON."""
    data = {
        "input": str(result.input_file),
        "method": result.method.value,
        "segments": [
            {
                "start": sp.start,
                "end": sp.end,
                "duration": round(sp.duration, 3),
                "label": sp.label,
                "confidence": sp.confidence,
            }
            for sp in result.split_points
        ],
        "output_files": [str(f) for f in result.output_files],
        "elapsed_seconds": round(result.elapsed_seconds, 3),
    }
    click.echo(json.dumps(data, indent=2))


class _noop:
    """No-op context manager for JSON mode."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


if __name__ == "__main__":
    main()
