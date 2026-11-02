"""SQLite persistence for local transcription jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False
    )


def make_engine(database_url: str, *, data_dir: Path) -> sessionmaker[Session]:
    if database_url.startswith("sqlite:"):
        data_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
