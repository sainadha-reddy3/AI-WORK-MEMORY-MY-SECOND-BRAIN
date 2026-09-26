/**
 * Backend API client.
 *
 * Every call to the backend goes through here, so changing the URL
 * or adding authentication later means editing one file.
 */

// Calls go to our own origin and are proxied to the backend by
// next.config.ts, which avoids cross-origin requests entirely.
const API_URL = "/api";

/* ---------- types ---------- */

export type Evidence = {
  id: string;
  source_type: string;
  source_detail: string | null;
  excerpt: string | null;
  attachment_id: string | null;
  created_at: string;
};

export type AttachmentBrief = {
  id: string;
  kind: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
};

export type Memory = {
  id: string;
  occurred_on: string;
  created_at: string;
  title: string;
  content: string;
  memory_type: string;
  confidence: string;
  topics: string[];
  project: string | null;
  language: string;
  raw_input: string | null;
  evidence: Evidence[];
  attachments: AttachmentBrief[];
};

export type MemoryCreate = {
  occurred_on: string;
  title: string;
  content: string;
  memory_type?: string;
  confidence?: string;
  topics?: string[];
  language?: string;
};

export type CapturePreview = {
  provider: string;
  ai_available: boolean;
  title: string;
  memory_type: string;
  confidence: string;
  topics: string[];
  language: string;
  uncertainty_markers: string[];
};

export type CaptureResult = {
  memory: Memory;
  preview: CapturePreview;
};

export type AskResponse = {
  question: string;
  has_recorded_memory: boolean;
  answer: string;
  general_knowledge: string | null;
  sources: Memory[];
  provider: string;
  provider_available: boolean;
};

export type TopicSummary = {
  topic: string;
  count: number;
  last_seen: string;
};

export type RelatedTopic = {
  topic: string;
  shared_memories: number;
};

export type TopicHistory = {
  topic: string;
  total: number;
  first_seen: string | null;
  last_seen: string | null;
  uncertain_count: number;
  timeline: Memory[];
  by_type: Record<string, Memory[]>;
  related_topics: RelatedTopic[];
};

export type UploadedAttachment = AttachmentBrief & {
  memory_id: string | null;
  sha256: string;
  created_at: string;
};

export type UploadResult = {
  attachment: UploadedAttachment;
  memory: Memory;
};

/* ---------- helpers ---------- */

// Turn an error response into a readable message. FastAPI puts the
// reason in `detail`, which is far more useful than the raw body.
async function errorMessage(res: Response, fallback: string): Promise<string> {
  const body = await res.text();
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // not JSON — fall through
  }
  return `${fallback} (${res.status})`;
}

/* ---------- memories ---------- */

export async function listMemories(): Promise<Memory[]> {
  const res = await fetch(`${API_URL}/memories`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to load memories"));
  return res.json();
}

export async function createMemory(data: MemoryCreate): Promise<Memory> {
  const res = await fetch(`${API_URL}/memories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to save memory"));
  return res.json();
}

// Create a memory from natural language. The AI proposes title, type
// and topics; the response includes what was inferred.
export async function captureMemory(text: string): Promise<CaptureResult> {
  const res = await fetch(`${API_URL}/memories/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to save memory"));
  return res.json();
}

/* ---------- ask ---------- */

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to ask"));
  return res.json();
}

/* ---------- topics ---------- */

export async function listTopics(): Promise<TopicSummary[]> {
  const res = await fetch(`${API_URL}/topics`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to load topics"));
  return res.json();
}

export async function getTopicHistory(topic: string): Promise<TopicHistory> {
  const res = await fetch(`${API_URL}/topics/${encodeURIComponent(topic)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await errorMessage(res, "Failed to load topic"));
  return res.json();
}

/* ---------- attachments ---------- */

// Upload a file as evidence. An optional note describes it and becomes
// an AI-structured memory; without one, nothing about the file's
// content is invented.
export async function uploadAttachment(file: File, note?: string): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  if (note && note.trim()) form.append("note", note.trim());

  const res = await fetch(`${API_URL}/attachments`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res, "Upload failed"));
  return res.json();
}

// URL of the original file, exactly as uploaded.
export function attachmentUrl(id: string): string {
  return `${API_URL}/attachments/${id}/file`;
}