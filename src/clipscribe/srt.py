"""SRT serialization for subtitle cues."""

from __future__ import annotations

from collections.abc import Sequence

from clipscribe.segmenter import SubtitleCue


def _format_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remaining = divmod(milliseconds, 3_600_000)
    minutes, remaining = divmod(remaining, 60_000)
    whole_seconds, milliseconds = divmod(remaining, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def export_srt(cues: Sequence[SubtitleCue]) -> str:
    """Return cues in SubRip format with one-based numbering."""
    blocks = [
        f"{index}\n{_format_timestamp(cue.start)} --> {_format_timestamp(cue.end)}\n{cue.text}"
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")
