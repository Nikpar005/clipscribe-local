from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from clipscribe.api import create_app
from clipscribe.database import Job


def completed_processor(job_id: str, *, sessions: sessionmaker[Session], jobs_dir: Path) -> None:
    with sessions() as session:
        job = session.get(Job, job_id)
        assert job is not None
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.transcript_json = json.dumps(
            [{"id": "1", "start": 0.0, "end": 1.0, "text": "Γεια σου."}],
            ensure_ascii=False,
        )
        session.commit()


def make_client(tmp_path: Path) -> TestClient:
    url = f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}"
    app = create_app(
        database_url=url,
        data_dir=tmp_path,
        processor=completed_processor,
    )
    return TestClient(app)


def test_upload_status_video_transcript_save_and_export(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/jobs",
            files={"video": ("sample.mp4", b"fake video bytes", "video/mp4")},
        )
        assert response.status_code == 202
        job_id = response.json()["id"]

        status = client.get(f"/jobs/{job_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "completed"

        video = client.get(f"/jobs/{job_id}/video")
        assert video.status_code == 200
        assert video.content == b"fake video bytes"

        transcript = client.get(f"/jobs/{job_id}/transcript")
        assert transcript.json()["segments"][0]["text"] == "Γεια σου."

        update = client.put(
            f"/jobs/{job_id}/transcript",
            json={"segments": [{"id": "1", "start": 0, "end": 1.2, "text": "Γεια σου!"}]},
        )
        assert update.status_code == 200

        exported = client.get(f"/jobs/{job_id}/export.srt")
        assert exported.status_code == 200
        assert exported.text == "1\n00:00:00,000 --> 00:00:01,200\nΓεια σου!\n"


def test_unknown_job_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/jobs/unknown").status_code == 404


def test_unsupported_video_format_is_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/jobs",
            files={"video": ("notes.txt", b"text", "text/plain")},
        )
    assert response.status_code == 415


def test_overlapping_cues_are_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/jobs",
            files={"video": ("sample.mp4", b"video", "video/mp4")},
        )
        job_id = created.json()["id"]
        response = client.put(
            f"/jobs/{job_id}/transcript",
            json={
                "segments": [
                    {"id": "1", "start": 0, "end": 1, "text": "First"},
                    {"id": "2", "start": 0.5, "end": 2, "text": "Second"},
                ]
            },
        )
    assert response.status_code == 422
