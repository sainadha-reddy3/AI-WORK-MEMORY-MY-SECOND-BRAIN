/**
 * Backend API client.
 *
 * Every call to the backend goes through here, so changing the URL
 * or adding authentication later means editing one file.
 */

// Calls go to our own origin and are proxied to the backend by
// next.config.ts, which avoids cross-origin requests entirely.
const API_URL = "/api";

export type Evidence = {
  id: string;
  source_type: string;
  source_detail: string | null;
  excerpt: string | null;
  created_at: string;
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

export async function listMemories(): Promise<Memory[]> {
  const res = await fetch(`${API_URL}/memories`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load memories (${res.status})`);
  return res.json();
}

export async function createMemory(data: MemoryCreate): Promise<Memory> {
  const res = await fetch(`${API_URL}/memories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to save memory (${res.status}): ${detail}`);
  }
  return res.json();
}

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

/**
 * Create a memory from natural language.
 *
 * The AI proposes title, type and topics; the response includes what
 * was inferred so it can be shown rather than applied invisibly.
 */
export async function captureMemory(text: string): Promise<CaptureResult> {
  const res = await fetch(`${API_URL}/memories/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to save memory (${res.status}): ${detail}`);
  }
  return res.json();
}
export type AskResponse = {
  question: string;
  has_recorded_memory: boolean;
  answer: string;
  general_knowledge: string | null;
  sources: Memory[];
  provider: string;
  provider_available: boolean;
};

/**
 * Ask a question about recorded history.
 *
 * Returns has_recorded_memory=false when nothing relevant exists —
 * the UI must show that clearly rather than hiding it.
 */
export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Failed to ask (${res.status}): ${detail}`);
  }
  return res.json();
}