from clipscribe.segmenter import SubtitleCue
from clipscribe.srt import export_srt


def test_export_srt_formats_numbering_times_and_multiline_text() -> None:
    content = export_srt(
        [
            SubtitleCue(0.0, 1.25, "Καλημέρα"),
            SubtitleCue(3661.234, 3663.0, "Πώς είσαι;\nΌλα καλά;"),
        ]
    )

    assert content == (
        "1\n00:00:00,000 --> 00:00:01,250\nΚαλημέρα\n\n"
        "2\n01:01:01,234 --> 01:01:03,000\nΠώς είσαι;\nΌλα καλά;\n"
    )


def test_empty_srt_is_empty() -> None:
    assert export_srt([]) == ""
