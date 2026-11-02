# Learnings

## Day 1

- A reliable transcription comparison needs hand-checked reference text, consistent clip boundaries, and documented provenance.
- Real-time factor is elapsed transcription time divided by audio duration; lower is faster, and measurements depend on hardware and model settings.
- Keep private or client footage out of the repository; benchmark material must be redistributable before it is committed.

## Day 2

- Extract audio to a predictable mono 16 kHz PCM WAV before transcription; this makes the inference input consistent.
- Keep word timestamps from the recognizer as raw evidence; segmentation and editorial corrections belong in later stages.
- faster-whisper can use CUDA FP16 or CPU int8, but GPU execution depends on matching CUDA and cuDNN libraries; CPU fallback keeps the pipeline usable when GPU setup fails.
