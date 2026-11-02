from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clipscribe.transcription import transcribe


class FakeModel:
    def __init__(self) -> None:
        self.path: str | None = None
        self.options: dict[str, Any] = {}

    def transcribe(self, path: str, **options: Any) -> tuple[list[Any], Any]:
        self.path = path
        self.options = options
        word = SimpleNamespace(start=0.1, end=0.4, word=" Γεια", probability=0.98)
        segment = SimpleNamespace(start=0.0, end=0.5, text=" Γεια σου", words=[word])
        info = SimpleNamespace(language="el", language_probability=0.99)
        return [segment], info


def test_transcribe_keeps_word_timestamps_and_language(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.touch()
    model = FakeModel()
    created: list[str] = []

    def make_model(model_name: str, *, device: str) -> FakeModel:
        created.append(f"{model_name}:{device}")
        return model

    monkeypatch.setattr("clipscribe.transcription._new_model", make_model)

    result = transcribe(audio, model_name="base", language="el")

    assert created == ["base:cuda"]
    assert model.path == str(audio)
    assert model.options == {"language": "el", "word_timestamps": True}
    assert result.language == "el"
    assert result.language_probability == pytest.approx(0.99)
    assert result.segments[0].text == "Γεια σου"
    assert result.segments[0].words[0].text == " Γεια"
    assert result.segments[0].words[0].start == pytest.approx(0.1)


def test_transcribe_falls_back_to_cpu_int8_when_cuda_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.touch()
    model = FakeModel()
    created: list[str] = []

    def make_model(model_name: str, *, device: str) -> FakeModel:
        created.append(device)
        if device == "cuda":
            raise OSError("CUDA libraries unavailable")
        return model

    monkeypatch.setattr("clipscribe.transcription._new_model", make_model)

    result = transcribe(audio)

    assert created == ["cuda", "cpu"]
    assert len(result.segments) == 1


def test_cpu_mode_skips_cuda(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.touch()
    model = FakeModel()
    created: list[str] = []

    def make_model(model_name: str, *, device: str) -> FakeModel:
        created.append(device)
        return model

    monkeypatch.setattr("clipscribe.transcription._new_model", make_model)

    transcribe(audio, device="cpu")

    assert created == ["cpu"]


def test_transcribe_requires_existing_audio(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Audio file does not exist"):
        transcribe(tmp_path / "missing.wav")
