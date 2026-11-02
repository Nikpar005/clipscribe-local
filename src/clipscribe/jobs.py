"""Job processing and transcript serialization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from sqlalchemy.orm import Session, sessionmaker

from clipscribe.audio import extract_audio
from clipscribe.database import Job
from clipscribe.segmenter import segment_words
from clipscribe.transcription import transcribe


class CueRecord(TypedDict):
    id: str
    start: float
    end: float
    text: str


def decode_cues(transcript_json: str | None) -> list[CueRecord]:
    if not transcript_json:
        return []
    value = json.loads(transcript_json)
    if not isinstance(value, list):
        raise TypeError("Stored transcript is not a list")
    cues: list[CueRecord] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError("Stored transcript cue is not an object")
        try:
            cues.append(
                {
                    "id": str(item["id"]),
                    "start": float(item["start"]),
                    "end": float(item["end"]),
                    "text": str(item["text"]),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Stored transcript cue is malformed") from exc
    return cues


def process_job(
    job_id: str,
    *,
    sessions: sessionmaker[Session],
    jobs_dir: Path,
) -> None:
    """Extract, transcribe, segment, and persist one queued job."""
    with sessions() as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.status = "processing"
        job.stage = "extracting_audio"
        job.progress = 5
        session.commit()
        source_path = Path(job.source_path)
        model_name = job.model_name

    work_dir = jobs_dir / job_id
    try:
        audio_path = extract_audio(source_path, work_dir / "audio.wav")
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.stage = "transcribing"
            job.progress = 20
            session.commit()

        result = transcribe(audio_path, model_name=model_name, language="el")
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.stage = "segmenting"
            job.progress = 85
            session.commit()

        words = tuple(word for segment in result.segments for word in segment.words)
        cues = segment_words(words)
        serialized = json.dumps(
            [
                {"id": str(index), "start": cue.start, "end": cue.end, "text": cue.text}
                for index, cue in enumerate(cues, start=1)
            ],
            ensure_ascii=False,
        )

        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.transcript_json = serialized
            job.stage = "completed"
            job.status = "completed"
            job.progress = 100
            job.error = None
            session.commit()
    # Record any processing failure on the job so polling clients can show it.
    except Exception as exc:  # noqa: BLE001
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is not None:
                job.status = "failed"
                job.stage = "failed"
                job.progress = 100
                job.error = str(exc)[:2000]
                session.commit()
