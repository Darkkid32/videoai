"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { api, Job, Character, Domain, Engine, Mode } from "@/lib/api";
import clsx from "clsx";

// ── Constants ─────────────────────────────────────────────────────────────────
const ENGINES = [
  { id: "wan"      as Engine, label: "Wan 2.1",   badge: "1.3B/T4", modes: ["t2v"] as Mode[], color: "from-blue-500/20 to-blue-900/10 border-blue-500/30" },
  { id: "flux"     as Engine, label: "FLUX.1",    badge: "Schnell", modes: ["t2i"]        as Mode[], color: "from-emerald-500/20 to-emerald-900/10 border-emerald-500/30" },
];

const DOMAINS: { id: Domain; label: string; desc: string }[] = [
  { id: "general",    label: "General",    desc: "Versatile generation" },
  { id: "cinematic",  label: "Cinematic",  desc: "Film-grade output" },
  { id: "influencer", label: "Influencer", desc: "Social media ready" },
];

const MODE_LABEL: Record<Mode, string> = { t2v: "Text → Video", i2v: "Image → Video", t2i: "Text → Image" };

const STATUS_COLORS: Record<string, string> = {
  queued:    "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  running:   "text-gold bg-gold/10 border-gold/20",
  done:      "text-green-400 bg-green-400/10 border-green-400/20",
  failed:    "text-red-400 bg-red-400/10 border-red-400/20",
  cancelled: "text-muted bg-dim/50 border-border",
};

type Panel = "generate" | "chat" | "jobs" | "characters" | "assets";

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [panel, setPanel] = useState<Panel>("generate");
  const [jobs, setJobs]   = useState<Job[]>([]);
  const [stats, setStats] = useState<{ total: number; done: number; running: number; queued: number; failed: number; avg_inference_seconds: number } | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [characters, setCharacters]   = useState<Character[]>([]);

  const refresh = useCallback(async () => {
    try {
      const [j, s, c] = await Promise.all([api.listJobs(60), api.jobStats(), api.listCharacters()]);
      setJobs(j);
      setStats(s);
      setCharacters(c);
      if (selectedJob) {
        const updated = j.find(x => x.id === selectedJob.id);
        if (updated) setSelectedJob(updated);
      }
    } catch {}
  }, [selectedJob]);

  useEffect(() => { refresh(); }, []);
  useEffect(() => {
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [refresh]);

  const runningCount = jobs.filter(j => j.status === "running").length;
  const queuedCount  = jobs.filter(j => j.status === "queued").length;

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-white">
      {/* ── Sidebar ── */}
      <aside className="w-16 flex-shrink-0 border-r border-border flex flex-col items-center py-4 gap-1 bg-surface z-10">
        {/* Logo */}
        <div className="mb-4">
          <div className="w-8 h-8 rounded-lg bg-gold-bg border border-gold-dim flex items-center justify-center">
            <span className="text-gold font-display font-bold text-xs">AI</span>
          </div>
        </div>

        {(["generate","chat","jobs","characters","assets"] as Panel[]).map(p => {
          const icons: Record<Panel, string> = {
            generate: "⚡", chat: "💬", jobs: "◎", characters: "◈", assets: "▦",
          };
          return (
            <button
              key={p}
              onClick={() => setPanel(p)}
              title={p.charAt(0).toUpperCase() + p.slice(1)}
              className={clsx(
                "w-10 h-10 rounded-lg flex items-center justify-center text-base transition-all relative",
                panel === p
                  ? "bg-gold-bg text-gold border border-gold-dim"
                  : "text-muted hover:text-white hover:bg-raised"
              )}
            >
              {icons[p]}
              {p === "jobs" && (runningCount + queuedCount) > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-gold text-black text-[8px] font-bold flex items-center justify-center">
                  {runningCount + queuedCount}
                </span>
              )}
            </button>
          );
        })}

        {/* GPU indicator */}
        <div className="mt-auto">
          <div className={clsx(
            "w-2 h-2 rounded-full mx-auto",
            runningCount > 0 ? "bg-gold animate-pulse-slow" : "bg-green/60"
          )} title={runningCount > 0 ? "GPU running" : "GPU idle"} />
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="flex-1 flex overflow-hidden">
        {panel === "generate" && (
          <GeneratePanel
            characters={characters}
            onJobSubmitted={() => { setPanel("jobs"); refresh(); }}
          />
        )}
        {panel === "chat" && (
          <ChatPanel onUsePrompt={(prompt) => {
            setPanel("generate");
            // Basic integration: a robust app would lift prompt state up or use a store
          }} />
        )}
        {panel === "jobs" && (
          <JobsPanel
            jobs={jobs}
            stats={stats}
            selectedJob={selectedJob}
            onSelect={setSelectedJob}
            onCancel={async (id) => { await api.cancelJob(id); refresh(); }}
          />
        )}
        {panel === "characters" && (
          <CharactersPanel characters={characters} onRefresh={refresh} />
        )}
        {panel === "assets" && (
          <AssetsPanel jobs={jobs.filter(j => j.status === "done" && j.output_url)} />
        )}
      </div>
    </div>
  );
}

// ── Generate Panel ────────────────────────────────────────────────────────────
function GeneratePanel({ characters, onJobSubmitted }: {
  characters: Character[];
  onJobSubmitted: () => void;
}) {
  const [engine, setEngine]         = useState<Engine>("wan");
  const [mode, setMode]             = useState<Mode>("t2v");
  const [domain, setDomain]         = useState<Domain>("cinematic");
  const [prompt, setPrompt]         = useState("");
  const [negPrompt, setNegPrompt]   = useState("");
  const [stylePrompt, setStylePrompt] = useState("");
  const [charId, setCharId]         = useState("");
  const [imageUrl, setImageUrl]     = useState("");
  const [optimizePrompt, setOptimizePrompt] = useState(true);
  const [advanced, setAdvanced]     = useState(false);
  const [steps, setSteps]           = useState("");
  const [cfg, setCfg]               = useState("");
  const [width, setWidth]           = useState("");
  const [height, setHeight]         = useState("");
  const [frames, setFrames]         = useState("");
  const [fps, setFps]               = useState("");
  const [seed, setSeed]             = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [uploadingImg, setUploadingImg] = useState(false);

  const activeEng = ENGINES.find(e => e.id === engine)!;

  useEffect(() => {
    if (!activeEng.modes.includes(mode)) setMode(activeEng.modes[0]);
  }, [engine]);

  async function submit() {
    if (!prompt.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.generate({
        engine, mode, content_domain: domain,
        prompt: prompt.trim(),
        negative_prompt: negPrompt || undefined,
        style_prompt: stylePrompt || undefined,
        input_image_url: imageUrl || undefined,
        character_id: charId || undefined,
        optimize_prompt: optimizePrompt,
        steps: steps ? +steps : undefined,
        cfg_scale: cfg ? +cfg : undefined,
        width: width ? +width : undefined,
        height: height ? +height : undefined,
        num_frames: frames ? +frames : undefined,
        fps: fps ? +fps : undefined,
        seed: seed ? +seed : undefined,
      });
      onJobSubmitted();
    } catch(e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImg(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImg(true);
    try { setImageUrl(await api.uploadImage(file)); }
    catch(e: any) { setError(e.message); }
    finally { setUploadingImg(false); }
  }

  return (
    <div className="w-[420px] flex-shrink-0 border-r border-border overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border grid-bg">
        <p className="text-xs font-mono text-gold uppercase tracking-widest mb-1">VideoAI</p>
        <h1 className="font-display text-2xl font-bold tracking-tight">Generate</h1>
      </div>

      <div className="p-6 flex flex-col gap-5 flex-1">
        {/* Engine */}
        <div>
          <Label>Engine</Label>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {ENGINES.map(eng => (
              <button
                key={eng.id}
                onClick={() => setEngine(eng.id)}
                className={clsx(
                  "p-3 rounded-xl border text-left transition-all",
                  engine === eng.id
                    ? `bg-gradient-to-b ${eng.color} glow-gold`
                    : "border-border bg-panel hover:bg-raised"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{eng.label}</span>
                  <span className="text-[9px] font-mono text-muted">{eng.badge}</span>
                </div>
                <div className="text-[10px] text-subtle leading-tight">
                  {eng.modes.join(" · ")}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Mode */}
        <div>
          <Label>Mode</Label>
          <div className="flex gap-2 mt-2 flex-wrap">
            {activeEng.modes.map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                  mode === m
                    ? "bg-gold-bg border-gold-dim text-gold"
                    : "border-border bg-panel text-subtle hover:text-white hover:border-dim"
                )}
              >
                {MODE_LABEL[m]}
              </button>
            ))}
          </div>
        </div>

        {/* Domain */}
        <div>
          <Label>Content Domain</Label>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {DOMAINS.map(d => (
              <button
                key={d.id}
                onClick={() => setDomain(d.id)}
                className={clsx(
                  "p-2.5 rounded-xl border text-left transition-all",
                  domain === d.id
                    ? "bg-gold-bg border-gold-dim text-gold"
                    : "border-border bg-panel text-subtle hover:text-white hover:border-dim"
                )}
              >
                <div className="text-xs font-semibold">{d.label}</div>
                <div className="text-[10px] mt-0.5 leading-tight opacity-70">{d.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* i2v image upload */}
        {mode === "i2v" && (
          <div>
            <Label>Reference Image</Label>
            <label className="mt-2 flex items-center gap-3 p-3 rounded-xl border border-dashed border-border bg-panel cursor-pointer hover:border-gold/40 transition-all group">
              <span className="text-lg">{imageUrl ? "✓" : "↑"}</span>
              <div>
                <div className={clsx("text-xs font-medium", imageUrl ? "text-green-400" : "text-subtle group-hover:text-white")}>
                  {uploadingImg ? "Uploading..." : imageUrl ? "Image ready" : "Upload reference image"}
                </div>
                {!imageUrl && <div className="text-[10px] text-muted mt-0.5">JPG, PNG, WebP</div>}
              </div>
              <input type="file" accept="image/*" className="hidden" onChange={handleImg} />
            </label>
          </div>
        )}

        {/* Character */}
        {characters.length > 0 && (
          <div>
            <Label>Character <span className="text-muted font-normal">(optional)</span></Label>
            <select
              value={charId}
              onChange={e => setCharId(e.target.value)}
              className="input-base mt-2 bg-raised"
            >
              <option value="">No character</option>
              {characters.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Prompt */}
        <div>
          <div className="flex items-center justify-between">
            <Label>Prompt</Label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <span className="text-[10px] text-muted">Auto-optimize</span>
              <div
                onClick={() => setOptimizePrompt(!optimizePrompt)}
                className={clsx(
                  "w-7 h-4 rounded-full transition-colors relative cursor-pointer",
                  optimizePrompt ? "bg-gold" : "bg-dim"
                )}
              >
                <div className={clsx(
                  "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all",
                  optimizePrompt ? "left-3.5" : "left-0.5"
                )} />
              </div>
            </label>
          </div>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder={domain === "cinematic"
              ? "A lone astronaut walks across a desolate red planet, cinematic wide shot..."
              : "Describe your scene in detail..."}
            rows={5}
            className="input-base mt-2 resize-none font-mono text-xs leading-relaxed"
          />
        </div>

        {/* Negative prompt */}
        <div>
          <Label>Negative Prompt</Label>
          <input
            value={negPrompt}
            onChange={e => setNegPrompt(e.target.value)}
            placeholder="blurry, low quality, watermark..."
            className="input-base mt-2 font-mono text-xs"
          />
        </div>

        {/* Style */}
        <div>
          <Label>Style Override <span className="text-muted font-normal">(optional)</span></Label>
          <input
            value={stylePrompt}
            onChange={e => setStylePrompt(e.target.value)}
            placeholder="oil painting style, neon noir, hyperrealistic..."
            className="input-base mt-2 font-mono text-xs"
          />
        </div>

        {/* Advanced */}
        <div>
          <button
            onClick={() => setAdvanced(!advanced)}
            className="flex items-center gap-2 text-xs text-muted hover:text-white transition-colors"
          >
            <span className={clsx("transition-transform text-[8px]", advanced && "rotate-90")}>▶</span>
            Advanced Parameters
          </button>
          {advanced && (
            <div className="mt-3 grid grid-cols-2 gap-2.5 animate-fade-in">
              {[
                ["Steps",   steps, setSteps,   engine === "wan" ? "12" : "4"],
                ["CFG",     cfg,   setCfg,     "5.0"],
                ["Width",   width, setWidth,   engine === "wan" ? "512" : "512"],
                ["Height",  height,setHeight,  engine === "wan" ? "320" : "512"],
                ["Frames",  frames,setFrames,  engine === "wan" ? "33" : "-"],
                ["FPS",     fps,   setFps,     engine === "wan" ? "8" : "-"],
                ["Seed",    seed,  setSeed,    "random"],
              ].map(([label, val, set, ph]: any) => (
                <div key={label}>
                  <div className="text-[10px] text-muted mb-1">{label}</div>
                  <input
                    value={val}
                    onChange={e => set(e.target.value)}
                    placeholder={ph}
                    className="w-full bg-dim border border-border rounded-lg px-2.5 py-2 text-xs font-mono
                      focus:outline-none focus:border-gold/40 placeholder:text-muted/50 transition-all"
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red/10 border border-red/20 rounded-xl p-3 text-xs text-red-400 font-mono">
            {error}
          </div>
        )}

        <button
          onClick={submit}
          disabled={submitting || !prompt.trim()}
          className="btn-primary w-full py-3 font-display text-base tracking-wide"
        >
          {submitting ? "Queuing job..." : "Generate ↗"}
        </button>
      </div>
    </div>
  );
}

// ── Jobs Panel ────────────────────────────────────────────────────────────────
function JobsPanel({ jobs, stats, selectedJob, onSelect, onCancel }: {
  jobs: Job[];
  stats: any;
  selectedJob: Job | null;
  onSelect: (j: Job) => void;
  onCancel: (id: string) => void;
}) {
  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Job list */}
      <div className="w-[360px] flex-shrink-0 border-r border-border flex flex-col overflow-hidden">
        {/* Stats bar */}
        <div className="px-4 py-3 border-b border-border bg-surface grid grid-cols-4 gap-2">
          {stats && [
            { label: "Total",   val: stats.total,   color: "text-white" },
            { label: "Done",    val: stats.done,    color: "text-green-400" },
            { label: "Running", val: stats.running, color: "text-gold" },
            { label: "Failed",  val: stats.failed,  color: "text-red-400" },
          ].map(s => (
            <div key={s.label} className="text-center">
              <div className={clsx("text-lg font-display font-bold", s.color)}>{s.val}</div>
              <div className="text-[9px] text-muted uppercase tracking-wider">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Job list */}
        <div className="flex-1 overflow-y-auto">
          {jobs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted text-sm">
              No jobs yet
            </div>
          ) : jobs.map(job => (
            <div
              key={job.id}
              onClick={() => onSelect(job)}
              className={clsx(
                "px-4 py-3 border-b border-border cursor-pointer transition-all group",
                selectedJob?.id === job.id ? "bg-raised" : "hover:bg-surface/60"
              )}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <p className="text-xs font-mono text-white/80 leading-tight line-clamp-2 flex-1">
                  {job.optimized_prompt || job.prompt}
                </p>
                <StatusBadge status={job.status} progress={job.progress} />
              </div>
              <div className="flex items-center gap-3 text-[10px] text-muted">
                <span className="font-mono">{job.engine}</span>
                <span>·</span>
                <span>{job.mode}</span>
                <span>·</span>
                <span className="capitalize">{job.content_domain}</span>
                {job.inference_time_seconds && (
                  <><span>·</span><span>{job.inference_time_seconds}s</span></>
                )}
              </div>
              {job.status === "running" && (
                <div className="mt-2 h-1 bg-dim rounded-full overflow-hidden">
                  <div
                    className="h-full progress-stripe rounded-full"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Job detail / preview */}
      <div className="flex-1 overflow-hidden">
        {selectedJob ? (
          <JobPreview job={selectedJob} onCancel={() => onCancel(selectedJob.id)} />
        ) : (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-muted grid-bg">
            <div className="text-4xl opacity-20">◎</div>
            <p className="text-sm">Select a job to preview</p>
          </div>
        )}
      </div>
    </div>
  );
}

function JobPreview({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const url = api.outputUrl(job.output_url);
  const isVideo = url?.endsWith(".mp4");

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-surface flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <StatusBadge status={job.status} progress={job.progress} />
          <div className="flex items-center gap-2">
            {(job.status === "queued" || job.status === "running") && (
              <button onClick={onCancel} className="text-xs text-muted hover:text-red-400 transition-colors">
                Cancel
              </button>
            )}
            {url && (
              <a href={url} download className="text-xs text-gold hover:text-amber-400 transition-colors font-medium">
                Download ↓
              </a>
            )}
          </div>
        </div>
        <p className="text-xs font-mono text-subtle leading-relaxed line-clamp-3">{job.optimized_prompt || job.prompt}</p>
        <div className="flex gap-3 mt-2 text-[10px] text-muted font-mono">
          <span>{job.engine}</span>
          <span>·</span><span>{job.mode}</span>
          <span>·</span><span className="capitalize">{job.content_domain}</span>
          {job.inference_time_seconds && <><span>·</span><span>{job.inference_time_seconds}s inference</span></>}
        </div>
      </div>

      {/* Media area */}
      <div className="flex-1 flex items-center justify-center p-8 bg-bg overflow-auto">
        {job.status === "queued" && (
          <div className="text-center animate-pulse-slow">
            <div className="text-4xl mb-3">◌</div>
            <p className="text-muted text-sm">Waiting in queue...</p>
          </div>
        )}

        {job.status === "running" && (
          <div className="text-center w-72">
            <div className="text-3xl mb-4 text-gold">◎</div>
            <div className="h-1.5 bg-dim rounded-full overflow-hidden mb-3">
              <div className="h-full progress-stripe rounded-full" style={{ width: `${job.progress}%` }} />
            </div>
            <p className="text-xs text-muted font-mono">{job.progress}% — generating</p>
          </div>
        )}

        {job.status === "failed" && (
          <div className="text-center max-w-sm">
            <div className="text-3xl mb-3 text-red-500">✕</div>
            <p className="text-red-400 text-sm font-semibold mb-2">Generation failed</p>
            <p className="text-muted text-xs font-mono leading-relaxed">{job.error}</p>
          </div>
        )}

        {job.status === "done" && url && (
          isVideo ? (
            <video
              src={url} controls autoPlay loop muted
              className="max-w-full max-h-full rounded-xl shadow-2xl animate-fade-in"
            />
          ) : (
            <img
              src={url} alt={job.prompt}
              className="max-w-full max-h-full rounded-xl shadow-2xl object-contain animate-fade-in"
            />
          )
        )}
      </div>
    </div>
  );
}

// ── Characters Panel ──────────────────────────────────────────────────────────
function CharactersPanel({ characters, onRefresh }: { characters: Character[]; onRefresh: () => void }) {
  const [creating, setCreating]   = useState(false);
  const [name, setName]           = useState("");
  const [description, setDesc]    = useState("");
  const [tags, setTags]           = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function create() {
    if (!name.trim() || !description.trim()) return;
    setSubmitting(true);
    try {
      await api.createCharacter({
        name: name.trim(),
        description: description.trim(),
        style_tags: tags ? tags.split(",").map(t => t.trim()).filter(Boolean) : [],
      });
      setCreating(false);
      setName(""); setDesc(""); setTags("");
      onRefresh();
    } catch {}
    finally { setSubmitting(false); }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-xl font-bold">Characters</h2>
            <p className="text-xs text-muted mt-1">Reusable character identities with LoRA support</p>
          </div>
          <button onClick={() => setCreating(!creating)} className="btn-primary px-4 py-2">
            + New Character
          </button>
        </div>

        {creating && (
          <div className="bg-panel border border-border rounded-2xl p-5 mb-5 animate-slide-up">
            <h3 className="text-sm font-semibold mb-4">New Character</h3>
            <div className="flex flex-col gap-3">
              <div>
                <Label>Name</Label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Sarah Chen" className="input-base mt-1.5" />
              </div>
              <div>
                <Label>Visual Description</Label>
                <textarea value={description} onChange={e => setDesc(e.target.value)}
                  placeholder="30-year-old woman, short black hair, sharp features, confident expression..."
                  rows={3} className="input-base mt-1.5 resize-none font-mono text-xs" />
              </div>
              <div>
                <Label>Style Tags <span className="text-muted font-normal">(comma-separated)</span></Label>
                <input value={tags} onChange={e => setTags(e.target.value)}
                  placeholder="cinematic, realistic, professional" className="input-base mt-1.5 font-mono text-xs" />
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={create} disabled={submitting} className="btn-primary">
                  {submitting ? "Creating..." : "Create Character"}
                </button>
                <button onClick={() => setCreating(false)} className="btn-ghost">Cancel</button>
              </div>
            </div>
          </div>
        )}

        {characters.length === 0 && !creating ? (
          <div className="text-center py-16 text-muted grid-bg rounded-2xl border border-border">
            <div className="text-3xl mb-3 opacity-30">◈</div>
            <p className="text-sm">No characters yet.</p>
            <p className="text-xs mt-1 opacity-60">Create one to use consistent identities across generations.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {characters.map(c => (
              <div key={c.id} className="bg-panel border border-border rounded-2xl p-4 hover:border-dim transition-all">
                <div className="flex items-start gap-3">
                  {c.reference_image_url ? (
                    <img src={api.outputUrl(c.reference_image_url) || ""} alt={c.name}
                      className="w-10 h-10 rounded-full object-cover flex-shrink-0" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-raised border border-border flex items-center justify-center text-muted text-sm flex-shrink-0">
                      {c.name[0]}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{c.name}</p>
                    <p className="text-xs text-muted mt-0.5 line-clamp-2">{c.description}</p>
                    {c.lora_path && <p className="text-[10px] text-gold mt-1 font-mono">LoRA attached</p>}
                  </div>
                </div>
                {c.style_tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {c.style_tags.map(tag => (
                      <span key={tag} className="text-[10px] px-2 py-0.5 bg-raised border border-border rounded-full text-muted">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Assets Panel ──────────────────────────────────────────────────────────────
function AssetsPanel({ jobs }: { jobs: Job[] }) {
  const [filter, setFilter] = useState<"all" | "video" | "image">("all");

  const filtered = jobs.filter(j => {
    if (filter === "video") return j.output_url?.endsWith(".mp4");
    if (filter === "image") return !j.output_url?.endsWith(".mp4");
    return true;
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-6 py-4 border-b border-border bg-surface flex items-center gap-4">
        <div>
          <h2 className="font-display text-lg font-bold">Asset Library</h2>
          <p className="text-xs text-muted">{filtered.length} assets</p>
        </div>
        <div className="ml-auto flex gap-1">
          {(["all","video","image"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={clsx("px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize",
                filter === f ? "bg-gold-bg text-gold border border-gold-dim" : "text-muted hover:text-white"
              )}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-muted grid-bg">
          <div className="text-3xl mb-3 opacity-20">▦</div>
          <p className="text-sm">No completed assets yet.</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-3 gap-3">
            {filtered.map(job => {
              const url = api.outputUrl(job.output_url);
              const isVideo = url?.endsWith(".mp4");
              return (
                <div key={job.id} className="group relative bg-panel border border-border rounded-xl overflow-hidden hover:border-dim transition-all aspect-video">
                  {isVideo ? (
                    <video src={url!} muted className="w-full h-full object-cover" />
                  ) : (
                    <img src={url!} alt={job.prompt} className="w-full h-full object-cover" />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all">
                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      <p className="text-[10px] font-mono text-white/80 line-clamp-1">{job.prompt}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[9px] text-muted">{job.engine} · {job.content_domain}</span>
                        <a href={url!} download className="text-[10px] text-gold hover:text-amber-400">↓</a>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Shared components ─────────────────────────────────────────────────────────
function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-xs font-medium text-subtle">{children}</div>;
}

function StatusBadge({ status, progress }: { status: string; progress: number }) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-mono font-medium flex-shrink-0",
      STATUS_COLORS[status] || STATUS_COLORS.queued
    )}>
      {status === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse-slow" />
      )}
      {status === "running" ? `${progress}%` : status}
    </span>
  );
}

// ── Chat Panel ────────────────────────────────────────────────────────────────
function ChatPanel({ onUsePrompt }: { onUsePrompt?: (prompt: string) => void }) {
  const [messages, setMessages] = useState<{role: string; content: string}[]>([
    { role: "system", content: "You are an uncensored AI assistant specifically tuned to help users brainstorm, script, and prompt for an 18+ content generation platform." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    
    try {
      const res = await api.chat(newMessages);
      setMessages([...newMessages, { role: "assistant", content: res.response }]);
    } catch (e: any) {
      setMessages([...newMessages, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg">
      <div className="px-6 py-4 border-b border-border bg-surface flex justify-between items-center">
        <div>
          <h2 className="font-display text-lg font-bold">Uncensored AI Assistant</h2>
          <p className="text-xs text-muted">Brainstorm scripts and prompts for generation</p>
        </div>
        <button onClick={() => api.unloadChat()} className="btn-ghost text-xs border border-border px-3 py-1.5 rounded-lg hover:bg-dim">Unload from GPU</button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.filter(m => m.role !== "system").map((m, i) => (
          <div key={i} className={clsx("flex flex-col max-w-[80%]", m.role === "user" ? "ml-auto items-end" : "mr-auto items-start")}>
            <div className={clsx(
              "px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed",
              m.role === "user" ? "bg-gold text-black rounded-tr-sm" : "bg-panel border border-border text-white/90 rounded-tl-sm"
            )}>
              {m.content}
            </div>
            <span className="text-[10px] text-muted mt-1 px-1 capitalize">{m.role}</span>
          </div>
        ))}
        {loading && (
          <div className="flex gap-1 p-4 w-16 items-center justify-center bg-panel border border-border rounded-2xl rounded-tl-sm">
            <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce"></span>
            <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce delay-100"></span>
            <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce delay-200"></span>
          </div>
        )}
        <div ref={endRef} />
      </div>
      
      <div className="p-4 border-t border-border bg-surface">
        <div className="max-w-4xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask the AI for ideas, scripts, or video prompts..."
            className="flex-1 input-base bg-panel py-3"
            disabled={loading}
          />
          <button 
            onClick={send} 
            disabled={!input.trim() || loading}
            className="btn-primary px-6"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
