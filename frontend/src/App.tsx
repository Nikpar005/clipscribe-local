import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Job = {
  id: string;
  filename: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: string;
  progress: number;
  error?: string | null;
};

type Cue = {
  id: string;
  start: number;
  end: number;
  text: string;
};

const stageLabels: Record<string, string> = {
  queued: "Waiting to start",
  extracting_audio: "Preparing audio",
  transcribing: "Listening and transcribing",
  segmenting: "Formatting subtitle segments",
  completed: "Ready to review",
  failed: "Could not process video",
};

function stamp(seconds: number): string {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const remaining = safe - minutes * 60;
  return `${String(minutes).padStart(2, "0")}:${remaining.toFixed(2).padStart(5, "0")}`;
}

export default function App() {
  const [job, setJob] = useState<Job | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [playhead, setPlayhead] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const activeCueId = useMemo(() => {
    return cues.find((cue) => playhead >= cue.start && playhead <= cue.end)?.id;
  }, [cues, playhead]);

  const loadTranscript = useCallback(async (jobId: string) => {
    const response = await fetch(`/jobs/${jobId}/transcript`);
    if (!response.ok) throw new Error("Could not load the transcript.");
    const data = (await response.json()) as { segments: Cue[] };
    setCues(data.segments);
  }, []);

  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "processing")) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/jobs/${job.id}`);
        if (!response.ok) throw new Error("Could not read job status.");
        const updated = (await response.json()) as Job;
        setJob(updated);
        if (updated.status === "completed") await loadTranscript(updated.id);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Status check failed.");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status, loadTranscript]);

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    const form = event.currentTarget;
    setBusy(true);
    setMessage("");
    setCues([]);
    try {
      const body = new FormData();
      body.append("video", file);
      const response = await fetch("/jobs", { method: "POST", body });
      const result = (await response.json()) as Job & { detail?: string };
      if (!response.ok) throw new Error(result.detail ?? "Upload failed.");
      setJob(result);
      setFile(null);
      form.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  function updateCue(id: string, field: keyof Cue, value: string) {
    setCues((current) =>
      current.map((cue) =>
        cue.id === id
          ? { ...cue, [field]: field === "text" || field === "id" ? value : Number(value) }
          : cue,
      ),
    );
  }

  async function saveTranscript() {
    if (!job) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/jobs/${job.id}/transcript`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments: cues }),
      });
      const data = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(data.detail ?? "Could not save changes.");
      setMessage("Changes saved on this computer.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save changes.");
    } finally {
      setBusy(false);
    }
  }

  function seekTo(seconds: number) {
    if (!videoRef.current) return;
    videoRef.current.currentTime = seconds;
    void videoRef.current.play();
  }

  const completed = job?.status === "completed";

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="ClipScribe Local home">
          <span className="brand-mark">C</span>
          <span>clipscribe<span className="brand-light">.local</span></span>
        </a>
        <span className="privacy-pill"><span className="privacy-dot" /> Private by design</span>
      </header>

      <section className="intro" id="top">
        <div className="eyebrow">LOCAL SUBTITLE WORKSPACE</div>
        <h1>Make every word <em>readable.</em></h1>
        <p>Transcribe, refine, and export subtitles on your own computer.</p>
      </section>

      {!job && (
        <section className="upload-card panel">
          <div className="card-kicker">01 <span>START A TRANSCRIPT</span></div>
          <h2>Choose a video</h2>
          <p className="muted">Your video stays on this computer. Supported: MP4, MOV, MKV, WebM, AVI.</p>
          <form onSubmit={upload} className="upload-form">
            <label
              className={`dropzone ${file ? "has-file" : ""}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const dropped = event.dataTransfer.files[0];
                if (dropped) setFile(dropped);
              }}
            >
              <input
                type="file"
                accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-msvideo,.m4v"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <span className="upload-icon">↑</span>
              <span className="drop-title">{file ? file.name : "Drop a video here or choose a file"}</span>
              <span className="drop-hint">Maximum file size: 2 GB</span>
            </label>
            <button className="button button-primary" disabled={!file || busy}>
              {busy ? "Uploading…" : "Create transcript"}<span aria-hidden="true">↗</span>
            </button>
          </form>
          {message && <p className="message error-message" role="alert">{message}</p>}
        </section>
      )}

      {job && (
        <>
          <section className="job-card panel">
            <div className="job-heading">
              <div>
                <div className="card-kicker">{completed ? "02" : "01"} <span>{completed ? "TRANSCRIPT READY" : "WORKING LOCALLY"}</span></div>
                <h2 className="file-name">{job.filename}</h2>
              </div>
              <button
                className="button button-quiet"
                onClick={() => { setJob(null); setCues([]); setMessage(""); }}
              >
                New video
              </button>
            </div>
            {!completed && job.status !== "failed" && (
              <div className="progress-area">
                <div className="progress-copy"><span>{stageLabels[job.stage] ?? "Processing"}</span><span>{job.progress}%</span></div>
                <div className="progress-track"><div className="progress-fill" style={{ width: `${job.progress}%` }} /></div>
                <p className="muted small">The first run downloads the speech model. Later runs can work offline.</p>
              </div>
            )}
            {job.status === "failed" && <p className="message error-message" role="alert">{job.error ?? "Processing failed."}</p>}
          </section>

          {completed && (
            <section className="workspace">
              <div className="video-panel panel">
                <div className="panel-heading"><div className="card-kicker">03 <span>VIDEO PREVIEW</span></div></div>
                <video ref={videoRef} controls preload="metadata" src={`/jobs/${job.id}/video`} onTimeUpdate={() => setPlayhead(videoRef.current?.currentTime ?? 0)} />
                <div className="video-caption"><span className="privacy-dot" /> Video playback is served from the local app.</div>
              </div>

              <div className="editor-panel panel">
                <div className="editor-heading">
                  <div><div className="card-kicker">04 <span>REVIEW & REFINE</span></div><h2>Subtitle segments</h2></div>
                  <span className="cue-count">{cues.length} cues</span>
                </div>
                <div className="cue-list">
                  {cues.map((cue, index) => (
                    <article className={`cue-row ${activeCueId === cue.id ? "cue-active" : ""}`} key={cue.id}>
                      <button className="cue-seek" onClick={() => seekTo(cue.start)} aria-label={`Seek to segment ${index + 1}`}>
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <span>{stamp(cue.start)} <small>↗</small></span>
                      </button>
                      <div className="cue-fields">
                        <textarea
                          aria-label={`Subtitle text ${index + 1}`}
                          value={cue.text}
                          rows={Math.max(2, cue.text.split("\n").length)}
                          onChange={(event) => updateCue(cue.id, "text", event.target.value)}
                        />
                        <div className="time-fields">
                          <label>In <input aria-label={`Start time ${index + 1}`} type="number" min="0" step="0.01" value={cue.start} onChange={(event) => updateCue(cue.id, "start", event.target.value)} /></label>
                          <label>Out <input aria-label={`End time ${index + 1}`} type="number" min="0" step="0.01" value={cue.end} onChange={(event) => updateCue(cue.id, "end", event.target.value)} /></label>
                          <span className="duration-label">{Math.max(0, cue.end - cue.start).toFixed(2)} sec</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
                <div className="editor-actions">
                  <span className="message" role="status">{message}</span>
                  <button className="button button-quiet" disabled={busy} onClick={saveTranscript}>Save changes</button>
                  <a className="button button-primary" href={`/jobs/${job.id}/export.srt`}>Export SRT <span aria-hidden="true">↓</span></a>
                </div>
              </div>
            </section>
          )}
        </>
      )}

      <footer><span>CLIPSCRIBE LOCAL</span><span>Runs on your machine · No cloud transcription</span></footer>
    </main>
  );
}
