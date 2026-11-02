"""Audio preparation helpers backed by the system FFmpeg executable."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def extract_audio(
    video_path: Path,
    output_path: Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
) -> Path:
    """Extract mono 16 kHz PCM WAV audio from a video file.

    The caller chooses the output path so job storage can control where temporary
    files live. The function creates its parent directory and returns the output path.
    """
    source = Path(video_path)
    destination = Path(output_path)

    if not source.is_file():
        raise FileNotFoundError(f"Video file does not exist: {source}")
    if shutil.which(ffmpeg_executable) is None:
        raise FileNotFoundError(
            f"FFmpeg executable '{ffmpeg_executable}' was not found on PATH. "
            "Install FFmpeg or pass its full executable path."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_executable,
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or "FFmpeg exited with an unknown error."
        raise RuntimeError(f"Audio extraction failed: {detail}")

    return destination
