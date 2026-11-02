# Learnings

## Day 1

- A reliable transcription comparison needs hand-checked reference text, consistent clip boundaries, and documented provenance.
- Real-time factor is elapsed transcription time divided by audio duration; lower is faster, and measurements depend on hardware and model settings.
- Keep private or client footage out of the repository; benchmark material must be redistributable before it is committed.

## Day 2

- Extract audio to a predictable mono 16 kHz PCM WAV before transcription; this makes the inference input consistent.
- Keep word timestamps from the recognizer as raw evidence; segmentation and editorial corrections belong in later stages.
- faster-whisper can use CUDA FP16 or CPU int8, but GPU execution depends on matching CUDA and cuDNN libraries; CPU fallback keeps the pipeline usable when GPU setup fails.

## Day 3

- A greedy segmenter can stay deterministic and pure while preferring punctuation and pauses at feasible cue boundaries.
- Character-per-second and minimum-duration targets may need cue ends to extend into silence; word timing and non-overlap limit how far they can extend.
- Keep line length, cue duration, reading speed, and pause thresholds configurable so Greek sample review can guide tuning instead of guessing permanently.

## Day 4

- Keep upload, processing status, transcript editing, and SRT export behind a small local API; the browser editor can then stay simple and focused.
- Local background work is convenient for a one-person desktop app, but a process restart loses in-flight work; persisted job state makes that limitation visible.
- GPU capability varies by installed CUDA and cuDNN libraries, so report the compute mode and preserve a CPU fallback instead of assuming the laptop GPU is ready.
- A benchmark runner should keep audio and reference text local, and report WER and real-time factor only from measured, checked samples.
