"""FastAPI application factory for local subtitle jobs."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from clipscribe.database import Job, make_engine
from clipscribe.jobs import decode_cues, process_job
from clipscribe.srt import export_srt

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024


class JobResponse(BaseModel):
    id: str
    filename: str
    status: str
    stage: str
    progress: int
    error: str | None = None


class CuePayload(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=1000)


class TranscriptPayload(BaseModel):
    segments: list[CuePayload]


def create_app(
    *,
    database_url: str | None = None,
    data_dir: Path | None = None,
    processor: Callable[..., None] = process_job,
) -> FastAPI:
    root = data_dir or Path(os.getenv("CLIPSCRIBE_DATA_DIR", "data"))
    jobs_dir = root / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    url = (
        database_url
        or os.getenv("CLIPSCRIBE_DATABASE_URL")
        or f"sqlite:///{(root / 'clipscribe.sqlite3').as_posix()}"
    )
    sessions = make_engine(url, data_dir=root)
    model_name = os.getenv("CLIPSCRIBE_MODEL", "small")
    app = FastAPI(title="clipscribe-local", version="0.1.0")
    app.state.sessions = sessions

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs", response_model=JobResponse, status_code=202)
    async def create_job(
        background_tasks: BackgroundTasks,
        video: UploadFile = File(...),  # noqa: B008 - FastAPI uses File to declare multipart input.
    ) -> JobResponse:
        filename = Path(video.filename or "video").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_VIDEO_SUFFIXES:
            raise HTTPException(status_code=415, detail="Unsupported video format")

        job_id = str(uuid.uuid4())
        job_dir = jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        source_path = job_dir / f"source{suffix}"
        total = 0
        try:
            with source_path.open("wb") as target:
                while chunk := await video.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail="Video exceeds 2 GB limit")
                    target.write(chunk)
        except Exception:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise
        finally:
            await video.close()

        if total == 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail="Uploaded video is empty")

        with sessions() as session:
            job = Job(
                id=job_id,
                filename=filename,
                source_path=str(source_path),
                model_name=model_name,
            )
            session.add(job)
            session.commit()

        background_tasks.add_task(
            processor,
            job_id,
            sessions=sessions,
            jobs_dir=jobs_dir,
        )
        return JobResponse(
            id=job_id,
            filename=filename,
            status="queued",
            stage="queued",
            progress=0,
        )

    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str) -> JobResponse:
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobResponse(
                id=job.id,
                filename=job.filename,
                status=job.status,
                stage=job.stage,
                progress=job.progress,
                error=job.error,
            )

    @app.get("/jobs/{job_id}/video")
    def get_video(job_id: str) -> FileResponse:
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            path = Path(job.source_path)
            filename = job.filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Video file not found")
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(path, filename=filename, media_type=media_type)

    @app.get("/jobs/{job_id}/transcript")
    def get_transcript(job_id: str) -> dict[str, object]:
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            if job.status != "completed" or job.transcript_json is None:
                raise HTTPException(status_code=409, detail="Transcript is not ready")
            return {"segments": decode_cues(job.transcript_json)}

    @app.put("/jobs/{job_id}/transcript")
    def update_transcript(job_id: str, payload: TranscriptPayload) -> dict[str, object]:
        previous_end = -1.0
        for segment in payload.segments:
            if segment.end <= segment.start:
                raise HTTPException(status_code=422, detail="Cue end must be after its start")
            if segment.start < previous_end:
                raise HTTPException(status_code=422, detail="Cues must be ordered and non-overlapping")
            if not segment.text.strip():
                raise HTTPException(status_code=422, detail="Cue text cannot be blank")
            previous_end = segment.end

        transcript_json = json.dumps(
            [segment.model_dump() for segment in payload.segments], ensure_ascii=False
        )
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            if job.status != "completed":
                raise HTTPException(status_code=409, detail="Job is not ready for editing")
            job.transcript_json = transcript_json
            session.commit()
        return {"segments": [segment.model_dump() for segment in payload.segments]}

    @app.get("/jobs/{job_id}/export.srt", response_class=PlainTextResponse)
    def export_transcript(job_id: str) -> PlainTextResponse:
        with sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Job not found")
            if job.status != "completed" or job.transcript_json is None:
                raise HTTPException(status_code=409, detail="Transcript is not ready")
            cues = decode_cues(job.transcript_json)

        from clipscribe.segmenter import SubtitleCue

        valid_cues = [
            SubtitleCue(
                start=cue["start"],
                end=cue["end"],
                text=cue["text"],
            )
            for cue in cues
        ]
        return PlainTextResponse(
            export_srt(valid_cues),
            media_type="application/x-subrip; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.srt"'},
        )

    return app
