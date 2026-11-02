# Segmentation design (initial v0.1 rules)

`segment_words` is a deterministic greedy pass over word-timed transcription. It grows a cue while it can fit the configured line and duration limits, then chooses the latest feasible punctuation or pause boundary. If neither exists, it uses the latest feasible word boundary. The function is pure: it does not mutate or reorder the word list.

Initial defaults:

- 42 characters per line and at most 2 lines, matching the Greek character limit published in the [Netflix Greek Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/235511047-Greek-Timed-Text-Style-Guide).
- 17 characters per second, the adult reading-speed limit in that same guide. This is a target, not a guarantee when adjacent speech leaves no display time to extend the cue.
- 0.8 seconds minimum cue duration, matching the approximately 20-frame minimum in the [Netflix timing guidelines](https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines).
- 6 seconds maximum cue duration and a 0.5-second pause threshold are project heuristics, exposed as function options so they can be tuned against the Greek sample set.

The cue end may extend beyond the last word into available silence to meet the minimum-duration and reading-speed targets. It stops at the next cue's start to avoid overlap. If no time is available, the audio's word timestamps take priority and the targets are best-effort. A single word longer than the configured line limit raises `ValueError`; the algorithm will not split a word and corrupt the transcript.

The greedy strategy is easy to inspect and explain. It does not globally optimize how all neighboring cues balance. The benchmark and manual editor review will show whether v0.1 needs a more sophisticated scoring approach.
