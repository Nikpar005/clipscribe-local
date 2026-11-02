from __future__ import annotations

import pytest

from clipscribe.segmenter import SubtitleCue, segment_words
from clipscribe.transcription import Word


def word(start: float, end: float, text: str) -> Word:
    return Word(start=start, end=end, text=text, probability=0.99)


def test_empty_input_returns_no_cues() -> None:
    assert segment_words([]) == []


def test_keeps_words_and_punctuation_without_extra_space() -> None:
    words = [
        word(0.0, 0.4, " Γεια"),
        word(0.4, 0.8, " σου,"),
        word(0.8, 1.3, " τι"),
        word(1.3, 1.8, " κάνεις;"),
    ]

    cues = segment_words(words)

    assert [cue.text for cue in cues] == ["Γεια σου,", "τι κάνεις;"]
    assert cues[0].start == 0.0
    assert cues[0].end <= cues[1].start
    assert " ".join(cue.text.replace("\n", " ") for cue in cues) == "Γεια σου, τι κάνεις;"


def test_prefers_sentence_punctuation_when_feasible() -> None:
    words = [
        word(0.0, 0.5, "Πάμε"),
        word(0.5, 1.0, "τώρα."),
        word(1.0, 1.5, "Είναι"),
        word(1.5, 2.0, "έτοιμοι."),
    ]

    cues = segment_words(words)

    assert [cue.text for cue in cues] == ["Πάμε τώρα.", "Είναι έτοιμοι."]


def test_prefers_a_pause_when_no_punctuation_is_available() -> None:
    words = [
        word(0.0, 0.4, "Έχουμε"),
        word(0.4, 0.8, "χρόνο"),
        word(1.5, 1.9, "για"),
        word(1.9, 2.4, "αυτό"),
    ]

    cues = segment_words(words)

    assert [cue.text for cue in cues] == ["Έχουμε χρόνο", "για αυτό"]


def test_wraps_at_42_characters_and_never_exceeds_two_lines() -> None:
    words = [word(index * 0.3, index * 0.3 + 0.2, " λέξη") for index in range(24)]

    cues = segment_words(words)

    assert len(cues) > 1
    for cue in cues:
        lines = cue.text.splitlines()
        assert 1 <= len(lines) <= 2
        assert all(len(line) <= 42 for line in lines)


def test_enforces_maximum_duration_except_for_an_indivisible_word() -> None:
    words = [word(index * 0.4, index * 0.4 + 0.2, " λέξη") for index in range(40)]

    cues = segment_words(words, max_duration_seconds=2.0)

    assert len(cues) > 1
    assert all(cue.end - cue.start <= 2.0 for cue in cues)


def test_extends_short_final_cue_for_readability() -> None:
    cues = segment_words([word(0.0, 0.2, " Ναι.")])

    assert cues == [SubtitleCue(start=0.0, end=0.8, text="Ναι.")]


def test_does_not_mutate_input() -> None:
    words = [word(0.0, 0.4, " Γεια"), word(0.4, 0.8, " σου.")]
    original = words.copy()

    segment_words(words)

    assert words == original


def test_rejects_a_word_longer_than_one_line() -> None:
    words = [word(0.0, 1.0, "α" * 43)]

    with pytest.raises(ValueError, match="exceeding the 42-character line limit"):
        segment_words(words)


def test_rejects_out_of_order_words() -> None:
    words = [word(1.0, 1.2, " δεύτερο"), word(0.0, 0.2, " πρώτο")]

    with pytest.raises(ValueError, match="ordered by start time"):
        segment_words(words)
