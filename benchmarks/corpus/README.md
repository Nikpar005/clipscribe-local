# Greek evaluation corpus

## Selected source

Use Mozilla Common Voice Scripted Speech, Greek (`el`), release 27.0, as the initial small evaluation source. It provides Greek speech recordings with corresponding validated text. The official dataset page lists the release as CC0-1.0, but its restrictions forbid re-hosting or re-sharing the dataset. Keep downloaded data and any extracted clips under `benchmarks/corpus/local/`; that directory is ignored by Git.

- Dataset page: <https://mozilladatacollective.com/datasets/cmu62fru800nko107kvyi4hrc>
- Dataset ID: `cmu62fru800nko107kvyi4hrc`
- Locale: `el`
- Type: scripted/read speech (not spontaneous creator video speech)
- Git policy: do not commit or attach the archive, selected audio, or dataset transcript rows

The corpus is a small reproducible ASR check, not a representative measure of Greek YouTube performance. Later, add a separate set of your own non-client clips if you choose and have permission to use them.

## Prepare the local sample

1. Open the official dataset page and download the Greek 27.0 archive using the page's download flow. Follow the site's current access terms; do not use third-party mirrors.
2. Extract it under `benchmarks/corpus/local/common-voice-el-27/`.
3. From `validated.tsv`, choose 8 rows with short, complete utterances. Prefer varied sentence length and avoid repeated speakers when the metadata allows it. Keep no speaker identifiers in project notes.
4. Listen to each selected recording and compare it with its supplied sentence. Exclude clips with mismatched text, clipped words, silence, or unintelligible audio. This listening check is our human verification; the original dataset validation alone is not enough to call it hand-checked.
5. Keep the chosen audio and reference text locally in the ignored `local/` folder. In the table below, note only IDs you assign yourself (for example `cv-el-01`), duration, broad speech style, and whether you checked the audio. Do not copy Common Voice sentences or filenames into this tracked file.

Keep each original utterance intact; Common Voice samples are short, generally a few seconds. Do not concatenate them, since sentence boundaries and recording conditions should remain clear.

## Local sample checklist

| Local ID | Duration | Style | Audio and reference listened through? | Eligible? |
|---|---:|---|---|---|

No clips are downloaded or checked yet. Do not report benchmark results until the checklist is populated and the local references have been verified.

## Limitations

This first set is read speech, so it will not test overlaps, spontaneous speech, background music, creator slang, or video-specific audio. Keep those limitations beside any WER result. Benchmark conclusions apply only to the selected sample, model, and recorded hardware settings.
