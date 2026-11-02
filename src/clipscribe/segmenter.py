"""Greedy, deterministic word-to-subtitle segmentation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from clipscribe.transcription import Word

_NO_SPACE_BEFORE = frozenset(",.!?;:…·)]}»”’%")
_CLOSING_QUOTES = frozenset("\"'’”»)]}")
_SENTENCE_ENDINGS = frozenset(".!?;…")  # Greek uses ';' as a question mark.
_CLAUSE_ENDINGS = frozenset(",:·")


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    """One subtitle cue. Newlines in ``text`` mark display line breaks."""

    start: float
    end: float
    text: str


def _token(word: Word) -> str:
    return word.text.strip()


def _join_tokens(words: Sequence[Word]) -> str:
    pieces: list[str] = []
    for word in words:
        token = _token(word)
        if not token:
            continue
        if pieces and token[0] not in _NO_SPACE_BEFORE:
            pieces.append(" ")
        pieces.append(token)
    return "".join(pieces)


def _wrap_words(
    words: Sequence[Word],
    *,
    max_chars_per_line: int,
    max_lines: int,
) -> tuple[str, ...] | None:
    lines = [""]
    for word in words:
        token = _token(word)
        if not token:
            continue
        if len(token) > max_chars_per_line:
            raise ValueError(
                f"A single word has {len(token)} characters, exceeding the "
                f"{max_chars_per_line}-character line limit: {token!r}"
            )

        separator = "" if not lines[-1] or token[0] in _NO_SPACE_BEFORE else " "
        proposed = f"{lines[-1]}{separator}{token}"
        if len(proposed) <= max_chars_per_line:
            lines[-1] = proposed
        else:
            if len(lines) >= max_lines:
                return None
            lines.append(token)

    return tuple(lines)


def _punctuation_rank(word: Word) -> int:
    token = _token(word).rstrip("".join(_CLOSING_QUOTES))
    if token and token[-1] in _SENTENCE_ENDINGS:
        return 2
    if token and token[-1] in _CLAUSE_ENDINGS:
        return 1
    return 0


def _group_end_time(words: Sequence[Word]) -> float:
    return max(word.end for word in words)


def _choose_group_end(
    words: Sequence[Word],
    *,
    start_index: int,
    max_chars_per_line: int,
    max_lines: int,
    min_duration_seconds: float,
    max_duration_seconds: float,
    pause_threshold_seconds: float,
) -> int:
    first_word = words[start_index]
    candidates: list[int] = []

    for end_index in range(start_index + 1, len(words) + 1):
        group = words[start_index:end_index]
        duration = _group_end_time(group) - first_word.start
        if end_index > start_index + 1 and duration > max_duration_seconds:
            break
        if _wrap_words(
            group,
            max_chars_per_line=max_chars_per_line,
            max_lines=max_lines,
        ) is None:
            break
        candidates.append(end_index)

    # A single long-duration word cannot be subdivided; preserve it intact.
    if len(candidates) == 1:
        return candidates[0]

    preferred: list[tuple[int, int]] = []
    for end_index in candidates:
        if end_index >= len(words):
            continue
        group = words[start_index:end_index]
        duration = _group_end_time(group) - first_word.start
        if duration < min_duration_seconds:
            continue

        previous = words[end_index - 1]
        following = words[end_index]
        is_pause = following.start - previous.end >= pause_threshold_seconds
        punctuation_rank = _punctuation_rank(previous)
        if is_pause or punctuation_rank:
            preferred.append((end_index, punctuation_rank))

    if preferred:
        preferred.sort(key=lambda item: (item[0], item[1]))
        return preferred[-1][0]

    long_enough = [
        end_index
        for end_index in candidates
        if _group_end_time(words[start_index:end_index]) - first_word.start
        >= min_duration_seconds
    ]
    return long_enough[-1] if long_enough else candidates[-1]


def segment_words(
    words: Sequence[Word],
    *,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
    min_duration_seconds: float = 0.8,
    max_duration_seconds: float = 6.0,
    max_characters_per_second: float = 17.0,
    pause_threshold_seconds: float = 0.5,
) -> list[SubtitleCue]:
    """Group word-timed transcription into readable subtitle cues.

    The function does not mutate or reorder its input. It prefers punctuation and
    pauses at feasible boundaries, then uses the latest boundary that fits the
    line and duration limits. Cue out-times may extend into available silence to
    meet minimum duration or reading-speed targets, without overlapping the next
    cue. When the audio leaves no such room, those timing targets are best-effort.
    """
    if max_chars_per_line < 1 or max_lines < 1:
        raise ValueError("Line limits must be positive integers")
    if min_duration_seconds < 0 or max_duration_seconds <= 0:
        raise ValueError("Cue durations must be non-negative and max duration positive")
    if min_duration_seconds > max_duration_seconds:
        raise ValueError("Minimum cue duration cannot exceed maximum cue duration")
    if max_characters_per_second <= 0:
        raise ValueError("Maximum characters per second must be positive")
    if pause_threshold_seconds < 0:
        raise ValueError("Pause threshold cannot be negative")

    previous_start = -math.inf
    for word in words:
        if not math.isfinite(word.start) or not math.isfinite(word.end):
            raise ValueError("Word timestamps must be finite")
        if word.start < 0 or word.end < word.start:
            raise ValueError("Word timestamps must be non-negative and end >= start")
        if word.start < previous_start:
            raise ValueError("Words must be ordered by start time")
        previous_start = word.start

    clean_words = tuple(word for word in words if _token(word))
    if not clean_words:
        return []

    groups: list[tuple[tuple[Word, ...], str, float, float]] = []
    index = 0
    while index < len(clean_words):
        end_index = _choose_group_end(
            clean_words,
            start_index=index,
            max_chars_per_line=max_chars_per_line,
            max_lines=max_lines,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
            pause_threshold_seconds=pause_threshold_seconds,
        )
        group = clean_words[index:end_index]
        lines = _wrap_words(
            group,
            max_chars_per_line=max_chars_per_line,
            max_lines=max_lines,
        )
        if lines is None:
            raise ValueError("Unable to wrap words within the configured line limits")
        groups.append((group, "\n".join(lines), group[0].start, _group_end_time(group)))
        index = end_index

    cues: list[SubtitleCue] = []
    for group_index, (group, text, start, raw_end) in enumerate(groups):
        character_count = len(text.replace("\n", " "))
        desired_duration = max(
            min_duration_seconds,
            character_count / max_characters_per_second,
        )
        desired_end = min(start + desired_duration, start + max_duration_seconds)
        end = max(raw_end, desired_end)

        if group_index + 1 < len(groups):
            next_start = groups[group_index + 1][2]
            if next_start >= raw_end:
                end = min(end, next_start)

        cues.append(SubtitleCue(start=start, end=end, text=text))

    return cues
