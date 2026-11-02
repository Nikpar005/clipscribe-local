"""Word-timed transcription through faster-whisper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class Word:
    """One recognized word and its audio-relative timestamps."""

    start: float
    end: float
    text: str
    probability: float | None


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """A Whisper segment containing words and its original segment text."""

    start: float
    end: float
    text: str
    words: tuple[Word, ...]


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Recognized speech before subtitle segmentation or editorial changes."""

    language: str
    language_probability: float | None
    segments: tuple[TranscriptSegment, ...]


def _new_model(model_name: str, *, device: Literal["cpu", "cuda"]) -> Any:
    # Import lazily so non-transcription code and unit tests do not need to load
    # the native inference runtime just by importing this module.
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def _run_transcription(
    model: Any,
    audio_path: Path,
    language: str,
) -> TranscriptionResult:
    raw_segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
    )

    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        words = tuple(
            Word(
                start=float(raw_word.start),
                end=float(raw_word.end),
                text=str(raw_word.word),
                probability=(
                    float(raw_word.probability)
                    if raw_word.probability is not None
                    else None
                ),
            )
            for raw_word in (raw_segment.words or ())
        )
        segments.append(
            TranscriptSegment(
                start=float(raw_segment.start),
                end=float(raw_segment.end),
                text=str(raw_segment.text).strip(),
                words=words,
            )
        )

    return TranscriptionResult(
        language=str(info.language),
        language_probability=(
            float(info.language_probability)
            if info.language_probability is not None
            else None
        ),
        segments=tuple(segments),
    )


def transcribe(
    audio_path: Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str = "el",
    device: Literal["auto", "cpu"] = "auto",
) -> TranscriptionResult:
    """Transcribe audio and retain word timestamps.

    ``auto`` tries CUDA FP16 first, then retries with CPU int8 if GPU setup or
    inference fails. Model files are downloaded by faster-whisper on first use
    and cached outside the project directory.
    """
    source = Path(audio_path)
    if not source.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {source}")

    if device == "cpu":
        return _run_transcription(_new_model(model_name, device="cpu"), source, language)

    try:
        gpu_model = _new_model(model_name, device="cuda")
        return _run_transcription(gpu_model, source, language)
    # Native backend failures vary by CUDA driver, library, and device setup.
    except Exception as gpu_error:  # noqa: BLE001
        try:
            cpu_model = _new_model(model_name, device="cpu")
            return _run_transcription(cpu_model, source, language)
        except Exception as cpu_error:
            raise RuntimeError(
                "Transcription failed on CUDA and the CPU int8 fallback. "
                f"CUDA error: {gpu_error}. CPU error: {cpu_error}."
            ) from cpu_error
