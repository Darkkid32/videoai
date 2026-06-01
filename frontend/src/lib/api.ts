const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Engine = "wan" | "cogvideo" | "flux";
export type Mode   = "t2v" | "i2v" | "t2i";
export type Domain = "general" | "cinematic" | "influencer";

export interface GenerateRequest {
  engine: Engine;
  mode: Mode;
  content_domain: Domain;
  prompt: string;
  negative_prompt?: string;
  style_prompt?: string;
  input_image_url?: string;
  character_id?: string;
  lora_path?: string;
  optimize_prompt?: boolean;
  steps?: number;
  cfg_scale?: number;
  width?: number;
  height?: number;
  num_frames?: number;
  fps?: number;
  seed?: number;
  priority?: number;
}

export interface Job {
  id: string;
  engine: string;
  mode: string;
  content_domain: string;
  prompt: string;
  optimized_prompt: string | null;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress: number;
  output_url: string | null;
  error: string | null;
  inference_time_seconds: number | null;
  lora_path: string | null;
  created_at: string;
}

export interface JobStats {
  total: number; done: number; running: number;
  queued: number; failed: number; avg_inference_seconds: number;
}

export interface Character {
  id: string;
  name: string;
  description: string;
  reference_image_url: string | null;
  lora_path: string | null;
  style_tags: string[];
  project_id: string | null;
  created_at: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  modes: string[];
  recommended_resolution: string;
  recommended_frames: number | null;
  vram_required_gb: number;
  description: string;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  generate:       (body: GenerateRequest) => req<Job>("/generate", { method: "POST", body: JSON.stringify(body) }),
  listJobs:       (limit = 50) => req<Job[]>(`/jobs?limit=${limit}`),
  getJob:         (id: string) => req<Job>(`/jobs/${id}`),
  jobStats:       () => req<JobStats>("/jobs/stats"),
  cancelJob:      (id: string) => req<void>(`/jobs/${id}`, { method: "DELETE" }),
  listCharacters: () => req<Character[]>("/characters"),
  createCharacter:(body: Partial<Character>) => req<Character>("/characters", { method: "POST", body: JSON.stringify(body) }),
  listModels:     () => req<ModelInfo[]>("/models"),
  uploadImage:    async (file: File): Promise<string> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/v1/generate/upload-image`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    return `${BASE}${data.url}`;
  },
  outputUrl: (url: string | null): string | null => {
    if (!url) return null;
    return url.startsWith("http") ? url : `${BASE}${url}`;
  },
  chat: (messages: {role: string; content: string}[]) => req<{response: string}>("/chat", { method: "POST", body: JSON.stringify({ messages }) }),
  unloadChat: () => req<{status: string}>("/chat/unload", { method: "POST" }),
};
