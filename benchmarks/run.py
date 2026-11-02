"""Benchmark faster-whisper models against a local Greek TSV manifest."""

from __future__ import annotations

import argparse
import csv
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import av
from jiwer import wer


@dataclass(frozen=True)
class Sample:
    audio_path: Path
    reference: str
    duration_seconds: float


def read_manifest(path: Path, limit: int | None) -> list[Sample]:
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark manifest not found: {path}")

    samples: list[Sample] = []
    with path.open(encoding="utf-8", newline="") as manifest_file:
        reader = csv.DictReader(manifest_file, delimiter="\t")
        if not {"audio_path", "reference"}.issubset(reader.fieldnames or []):
            raise ValueError("Manifest must have audio_path and reference columns")
        for row in reader:
            raw_audio_path = (row.get("audio_path") or "").strip()
            reference = (row.get("reference") or "").strip()
            if not raw_audio_path or not reference:
                continue
            audio_path = Path(raw_audio_path)
            if not audio_path.is_absolute():
                audio_path = path.parent / audio_path
            if not audio_path.is_file():
                raise FileNotFoundError(f"Audio clip not found: {audio_path}")
            with av.open(str(audio_path)) as container:
                if container.duration is None:
                    raise ValueError(f"Could not read clip duration: {audio_path}")
                duration = container.duration / av.time_base
            samples.append(Sample(audio_path, reference, float(duration)))
            if limit is not None and len(samples) >= limit:
                break

    if not samples:
        raise ValueError("Manifest has no usable clips")
    return samples


def create_model(model_name: str, device: str):
    from faster_whisper import WhisperModel

    if device == "cpu":
        return WhisperModel(model_name, device="cpu", compute_type="int8"), "cpu/int8"
    try:
        return WhisperModel(model_name, device="cuda", compute_type="float16"), "cuda/float16"
    except Exception as error:  # noqa: BLE001 - CUDA setup errors vary across systems.
        print(f"CUDA unavailable for {model_name}; using CPU int8 ({error})")
        return WhisperModel(model_name, device="cpu", compute_type="int8"), "cpu/int8"


def run_model(model_name: str, device: str, samples: list[Sample]) -> dict[str, object]:
    model, compute = create_model(model_name, device)
    references: list[str] = []
    hypotheses: list[str] = []
    inference_seconds = 0.0
    audio_seconds = sum(sample.duration_seconds for sample in samples)

    for sample in samples:
        start = time.perf_counter()
        segments, _ = model.transcribe(str(sample.audio_path), language="el")
        hypothesis = " ".join(segment.text.strip() for segment in segments).strip()
        inference_seconds += time.perf_counter() - start
        references.append(sample.reference)
        hypotheses.append(hypothesis)

    return {
        "model": model_name,
        "compute": compute,
        "clips": len(samples),
        "audio_seconds": audio_seconds,
        "inference_seconds": inference_seconds,
        "rtf": inference_seconds / audio_seconds if audio_seconds else 0.0,
        "wer": float(wer(" ".join(references), " ".join(hypotheses))),
    }


def format_results(results: list[dict[str, object]], machine: str) -> str:
    lines = [
        f"Benchmark machine: {machine}",
        "",
        "Model load and any first-run download are excluded from RTF. Inference time includes all listed clips.",
        "",
        "| Model | Compute | Clips | Audio (s) | Inference (s) | RTF | WER |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            "| {model} | {compute} | {clips} | {audio:.1f} | {inference:.1f} | "
            "{rtf:.3f} | {wer:.3f} |".format(
                model=result["model"],
                compute=result["compute"],
                clips=result["clips"],
                audio=float(result["audio_seconds"]),
                inference=float(result["inference_seconds"]),
                rtf=float(result["rtf"]),
                wer=float(result["wer"]),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("benchmarks/corpus/local/sample.tsv"),
        help="Local-only TSV with audio_path and reference columns",
    )
    parser.add_argument("--models", default="tiny,base,small")
    parser.add_argument("--device", choices=("auto", "cpu"), default="auto")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", type=Path, help="Optional Markdown output path")
    args = parser.parse_args()

    samples = read_manifest(args.manifest, args.limit if args.limit > 0 else None)
    results = [run_model(model.strip(), args.device, samples) for model in args.models.split(",")]
    report = format_results(results, f"{platform.platform()}, Python {platform.python_version()}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
