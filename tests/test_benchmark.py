import csv
import wave
from pathlib import Path

import pytest
from benchmarks.run import format_results, read_manifest


def make_silent_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(16000)
        audio_file.writeframes(b"\0\0" * 16000)


def test_manifest_resolves_audio_relative_to_manifest(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    make_silent_wav(audio_path)
    manifest_path = tmp_path / "sample.tsv"
    with manifest_path.open("w", encoding="utf-8", newline="") as manifest:
        writer = csv.DictWriter(manifest, fieldnames=["audio_path", "reference"], delimiter="\t")
        writer.writeheader()
        writer.writerow({"audio_path": "audio.wav", "reference": "καλημέρα"})

    samples = read_manifest(manifest_path, limit=None)

    assert len(samples) == 1
    assert samples[0].audio_path == audio_path
    assert samples[0].reference == "καλημέρα"
    assert samples[0].duration_seconds == pytest.approx(1.0)


def test_manifest_rejects_missing_columns(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.tsv"
    manifest_path.write_text("path\ttext\na.wav\thello\n", encoding="utf-8")

    with pytest.raises(ValueError, match="audio_path and reference"):
        read_manifest(manifest_path, limit=None)


def test_report_displays_model_and_scores() -> None:
    report = format_results(
        [{
            "model": "small",
            "compute": "cpu/int8",
            "clips": 1,
            "audio_seconds": 10.0,
            "inference_seconds": 5.0,
            "rtf": 0.5,
            "wer": 0.1,
        }],
        "test machine",
    )

    assert "| small | cpu/int8 | 1 | 10.0 | 5.0 | 0.500 | 0.100 |" in report
