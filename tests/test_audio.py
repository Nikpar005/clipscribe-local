from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from clipscribe.audio import extract_audio


def test_extract_audio_builds_mono_16khz_pcm_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "input.mp4"
    source.touch()
    destination = tmp_path / "nested" / "audio.wav"
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr("clipscribe.audio.shutil.which", lambda _: "ffmpeg")
    monkeypatch.setattr("clipscribe.audio.subprocess.run", run)

    result = extract_audio(source, destination)

    assert result == destination
    assert destination.parent.is_dir()
    command = run.call_args.args[0]
    assert command[:5] == ["ffmpeg", "-nostdin", "-y", "-i", str(source)]
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-c:a") + 1] == "pcm_s16le"
    assert command[-1] == str(destination)


def test_extract_audio_requires_existing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Video file does not exist"):
        extract_audio(tmp_path / "missing.mp4", tmp_path / "audio.wav")


def test_extract_audio_reports_missing_ffmpeg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "input.mp4"
    source.touch()
    monkeypatch.setattr("clipscribe.audio.shutil.which", lambda _: None)

    with pytest.raises(FileNotFoundError, match="was not found on PATH"):
        extract_audio(source, tmp_path / "audio.wav")


def test_extract_audio_reports_ffmpeg_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "input.mp4"
    source.touch()
    failed = subprocess.CompletedProcess([], 1, "", "unsupported input")
    monkeypatch.setattr("clipscribe.audio.shutil.which", lambda _: "ffmpeg")
    monkeypatch.setattr("clipscribe.audio.subprocess.run", Mock(return_value=failed))

    with pytest.raises(RuntimeError, match="unsupported input"):
        extract_audio(source, tmp_path / "audio.wav")
