"use client";

import { useEffect, useState } from "react";
import {
  captureMemory,
  listMemories,
  type CapturePreview,
  type Memory,
} from "@/lib/api";

export default function Home() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPreview, setLastPreview] = useState<CapturePreview | null>(null);

  // Load existing memories once when the page opens.
  useEffect(() => {
    listMemories()
      .then(setMemories)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    const text = input.trim();
    if (!text) return;

    setSaving(true);
    setError(null);
    try {
      // The AI proposes structure — we no longer send a title or type.
      const { memory, preview } = await captureMemory(text);
      setMemories([memory, ...memories]);
      setLastPreview(preview);
      setInput("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-[#0b1020] text-slate-200">

      {/* ---------- TOP BAR ---------- */}
      <header className="flex h-16 shrink-0 items-center gap-4 border-b border-slate-800 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-lg">
            🧠
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white">My Work Memory</h1>
            <p className="text-[11px] text-slate-500">Remember. Learn. Grow.</p>
          </div>
        </div>

        <div className="mx-auto w-full max-w-xl">
          <input
            type="text"
            placeholder="Search your memory... (e.g. ArgoCD, GKE, pod issue)"
            className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm placeholder-slate-500 outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded-md border border-slate-800 px-2 py-1 text-xs text-slate-400">
            EN
          </span>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500 text-xs font-medium text-white">
            SR
          </div>
        </div>
      </header>

      {/* ---------- THREE PANELS ---------- */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT */}
        <aside className="w-64 shrink-0 overflow-y-auto border-r border-slate-800 p-4">
          <button className="mb-4 w-full rounded-lg bg-indigo-600 px-3 py-2 text-left text-sm font-medium text-white">
            💬 New Chat
          </button>

          <NavItem label="🕐 Reconstruct My Day" />
          <NavItem label="➕ Add Memory" />

          <SectionLabel text="MY MEMORY" />
          <NavItem label="📚 All Memories" count={memories.length} />

          <SectionLabel text="PROJECTS / TOPICS" />
          {topicCounts(memories).length === 0 ? (
            <p className="px-2 text-xs text-slate-600">No topics yet</p>
          ) : (
            topicCounts(memories).map(([topic, n]) => (
              <NavItem key={topic} label={`# ${topic}`} count={n} />
            ))
          )}
        </aside>

        {/* CENTER */}
        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="border-b border-slate-800 px-6 py-4">
            <h2 className="text-lg font-semibold text-white">Chat</h2>
            <p className="text-xs text-slate-500">
              Ask about your work, find past solutions, learn, or add new memories.
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <p className="text-center text-sm text-slate-500">Loading…</p>
            ) : memories.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center">
                <div>
                  <div className="mb-3 text-4xl">🧠</div>
                  <p className="text-sm text-slate-400">Your memory is empty.</p>
                  <p className="mt-1 text-xs text-slate-600">
                    Tell me what you worked on today and I&apos;ll remember it.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {memories.map((m) => (
                  <MemoryCard key={m.id} memory={m} />
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-slate-800 p-4">
            {error && (
              <p className="mb-2 rounded-md border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-300">
                {error}
              </p>
            )}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <textarea
                rows={2}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What did you work on? e.g. Fixed an ArgoCD sync failure..."
                className="w-full resize-none bg-transparent text-sm placeholder-slate-500 outline-none"
              />
              <div className="mt-2 flex items-center gap-2">
                <Chip label="📎 Attach" />
                <Chip label="🖼️ Screenshot" />
                <Chip label="🎤 Voice" />
                <button
                  onClick={handleSave}
                  disabled={saving || !input.trim()}
                  className="ml-auto rounded-lg bg-indigo-600 px-4 py-1.5 text-sm text-white disabled:opacity-40"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT */}
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-800 p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">
            What the AI understood
          </h3>
          {lastPreview ? (
            <PreviewPanel preview={lastPreview} />
          ) : (
            <div className="rounded-lg border border-slate-800 p-4 text-center">
              <p className="text-xs text-slate-500">
                Save a memory to see what was extracted.
              </p>
            </div>
          )}

          <h3 className="mb-3 mt-6 text-sm font-semibold text-white">Studio</h3>
          <div className="grid grid-cols-2 gap-2">
            <StudioButton label="📝 Summary" />
            <StudioButton label="🗺️ Mind Map" />
            <StudioButton label="📚 Learn More" />
            <StudioButton label="🗓️ Timeline" />
          </div>
        </aside>

      </div>
    </div>
  );
}

/* ---------- helpers ---------- */

function topicCounts(memories: Memory[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const m of memories) {
    for (const t of m.topics) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function PreviewPanel({ preview }: { preview: CapturePreview }) {
  return (
    <div className="space-y-3 rounded-lg border border-slate-800 p-3">
      <Row label="Title" value={preview.title} />
      <Row label="Type" value={preview.memory_type} />

      <div>
        <p className="text-[10px] uppercase tracking-wider text-slate-600">
          Confidence
        </p>
        <p
          className={
            preview.confidence === "uncertain"
              ? "text-xs text-amber-300"
              : "text-xs text-slate-300"
          }
        >
          {preview.confidence}
          {preview.uncertainty_markers.length > 0 && (
            <span className="text-slate-500">
              {" "}
              — you said &ldquo;{preview.uncertainty_markers.join('", "')}
              &rdquo;
            </span>
          )}
        </p>
      </div>

      {preview.topics.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-600">
            Topics
          </p>
          <div className="flex flex-wrap gap-1">
            {preview.topics.map((t) => (
              <span
                key={t}
                className="rounded bg-indigo-950/60 px-1.5 py-0.5 text-[10px] text-indigo-300"
              >
                #{t}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-slate-800 pt-2">
        <p className="text-[10px] text-slate-600">
          Provider: {preview.provider}
          {!preview.ai_available && " (unavailable — used rules)"}
        </p>
        <p className="mt-1 text-[10px] leading-relaxed text-slate-600">
          Title, type and topics are AI interpretation. Your original
          words are stored unchanged.
        </p>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-slate-600">
        {label}
      </p>
      <p className="text-xs text-slate-300">{value}</p>
    </div>
  );
}

function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-xs text-slate-500">{memory.occurred_on}</span>
        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
          {memory.memory_type}
        </span>
        {memory.confidence === "uncertain" && (
          <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[10px] text-amber-300">
            uncertain
          </span>
        )}
      </div>
      <h4 className="text-sm font-medium text-white">{memory.title}</h4>
      <p className="mt-1 text-xs leading-relaxed text-slate-400">
        {memory.content}
      </p>
      {memory.topics.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {memory.topics.map((t) => (
            <span
              key={t}
              className="rounded bg-indigo-950/60 px-1.5 py-0.5 text-[10px] text-indigo-300"
            >
              #{t}
            </span>
          ))}
        </div>
      )}
      <p className="mt-2 text-[10px] text-slate-600">
        Source: {memory.evidence.map((e) => e.source_type).join(", ") || "none"}
      </p>
    </div>
  );
}

function NavItem({ label, count }: { label: string; count?: number }) {
  return (
    <div className="flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800/60">
      <span className="truncate">{label}</span>
      {count !== undefined && (
        <span className="text-xs text-slate-500">{count}</span>
      )}
    </div>
  );
}

function SectionLabel({ text }: { text: string }) {
  return (
    <p className="mb-1 mt-5 px-2 text-[10px] font-semibold tracking-wider text-slate-600">
      {text}
    </p>
  );
}

function Chip({ label }: { label: string }) {
  return (
    <button className="rounded-md border border-slate-800 px-2.5 py-1 text-xs text-slate-400 hover:bg-slate-800/60">
      {label}
    </button>
  );
}

function StudioButton({ label }: { label: string }) {
  return (
    <button className="rounded-lg border border-slate-800 px-3 py-3 text-left text-xs text-slate-300 hover:bg-slate-800/60">
      {label}
    </button>
  );
}