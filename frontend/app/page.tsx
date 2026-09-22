"use client";

import { useEffect, useState } from "react";
import {
  askQuestion,
  captureMemory,
  listMemories,
  type AskResponse,
  type CapturePreview,
  type Memory,
} from "@/lib/api";

export default function Home() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [input, setInput] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPreview, setLastPreview] = useState<CapturePreview | null>(null);

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

  async function handleAsk() {
    const q = question.trim();
    if (!q) return;

    setAsking(true);
    setError(null);
    try {
      setAnswer(await askQuestion(q));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-[#0b1020] text-slate-200">

      {/* ---------- TOP BAR ---------- */}
      <header className="flex h-16 shrink-0 items-center gap-4 border-b border-slate-800 px-5">
        <div className="flex shrink-0 items-center gap-3">
          <MemoryLogo active={asking || saving} />
          <div className="hidden sm:block">
            <h1 className="text-sm font-semibold text-white">My Work Memory</h1>
            <p className="text-[11px] text-slate-500">Remember. Learn. Grow.</p>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-xl gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder="Ask your memory... (e.g. What did I do with ArgoCD?)"
            className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm placeholder-slate-500 outline-none focus:border-indigo-500"
          />
          <button
            onClick={handleAsk}
            disabled={asking || !question.trim()}
            className="shrink-0 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-40"
          >
            {asking ? "…" : "Ask"}
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden rounded-md border border-slate-800 px-2 py-1 text-xs text-slate-400 sm:block">
            EN
          </span>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500 text-xs font-medium text-white">
            SR
          </div>
        </div>
      </header>

      {/* ---------- THREE PANELS ---------- */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT — hidden on narrow screens so the conversation keeps room */}
        <aside className="hidden w-56 shrink-0 overflow-y-auto border-r border-slate-800 p-4 md:block lg:w-64">
          <button
            onClick={() => setAnswer(null)}
            className="mb-4 w-full rounded-lg bg-indigo-600 px-3 py-2 text-left text-sm font-medium text-white"
          >
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
              <button
                key={topic}
                onClick={() => {
                  setQuestion(topic);
                  askQuestion(topic).then(setAnswer).catch(() => {});
                }}
                className="flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-left text-sm text-slate-300 hover:bg-slate-800/60"
              >
                <span className="truncate"># {topic}</span>
                <span className="text-xs text-slate-500">{n}</span>
              </button>
            ))
          )}
        </aside>

        {/* CENTER */}
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="border-b border-slate-800 px-6 py-4">
            <h2 className="text-lg font-semibold text-white">
              {answer ? "Answer" : "Chat"}
            </h2>
            <p className="text-xs text-slate-500">
              {answer
                ? "Answered from your recorded memories only."
                : "Ask about your work, find past solutions, or add new memories."}
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {answer ? (
              <AnswerPanel answer={answer} />
            ) : loading ? (
              <p className="text-center text-sm text-slate-500">Loading…</p>
            ) : memories.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center">
                <div>
                  <div className="mb-3 flex justify-center">
                    <MemoryLogo size={56} active />
                  </div>
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

        {/* RIGHT — needs more room, so appears only on wider screens */}
        <aside className="hidden w-64 shrink-0 overflow-y-auto border-l border-slate-800 p-4 md:block xl:w-80">
          <h3 className="mb-3 text-sm font-semibold text-white">
            {answer ? "Sources" : "What the AI understood"}
          </h3>

          {answer ? (
            answer.sources.length === 0 ? (
              <div className="rounded-lg border border-slate-800 p-4 text-center">
                <p className="text-xs text-slate-500">
                  No sources — nothing recorded on this.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {answer.sources.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-lg border border-slate-800 p-3"
                  >
                    <p className="text-[10px] text-slate-500">
                      {s.occurred_on}
                    </p>
                    <p className="text-xs text-slate-300">{s.title}</p>
                    <p className="mt-1 text-[10px] text-slate-600">
                      Source: {s.evidence.map((e) => e.source_type).join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            )
          ) : lastPreview ? (
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

/* ---------- logo ---------- */

/**
 * Animated neural-network mark.
 *
 * Pure SVG with native <animate> elements — no CSS, no images, no
 * external files. Nodes pulse and connections shimmer, suggesting
 * memory forming. `active` speeds it up while work is happening.
 */
function MemoryLogo({
  size = 36,
  active = false,
}: {
  size?: number;
  active?: boolean;
}) {
  const speed = active ? "0.9s" : "2.8s";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="awmBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <radialGradient id="awmGlow">
          <stop offset="0%" stopColor="#c7d2fe" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#c7d2fe" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect width="48" height="48" rx="12" fill="url(#awmBg)" />

      {/* soft breathing glow behind the network */}
      <circle cx="24" cy="24" r="16" fill="url(#awmGlow)">
        <animate
          attributeName="opacity"
          values="0.25;0.6;0.25"
          dur={speed}
          repeatCount="indefinite"
        />
      </circle>

      {/* connections */}
      <g stroke="#e0e7ff" strokeWidth="1.2" strokeLinecap="round">
        <line x1="24" y1="24" x2="14" y2="14">
          <animate
            attributeName="opacity"
            values="0.2;0.85;0.2"
            dur={speed}
            repeatCount="indefinite"
          />
        </line>
        <line x1="24" y1="24" x2="34" y2="15">
          <animate
            attributeName="opacity"
            values="0.85;0.2;0.85"
            dur={speed}
            repeatCount="indefinite"
          />
        </line>
        <line x1="24" y1="24" x2="13" y2="31">
          <animate
            attributeName="opacity"
            values="0.4;0.9;0.4"
            dur={speed}
            begin="0.3s"
            repeatCount="indefinite"
          />
        </line>
        <line x1="24" y1="24" x2="33" y2="33">
          <animate
            attributeName="opacity"
            values="0.9;0.3;0.9"
            dur={speed}
            begin="0.6s"
            repeatCount="indefinite"
          />
        </line>
        <line x1="14" y1="14" x2="34" y2="15" opacity="0.3" />
        <line x1="13" y1="31" x2="33" y2="33" opacity="0.3" />
      </g>

      {/* outer nodes */}
      <g fill="#e0e7ff">
        <circle cx="14" cy="14" r="3">
          <animate
            attributeName="r"
            values="2.4;3.4;2.4"
            dur={speed}
            repeatCount="indefinite"
          />
        </circle>
        <circle cx="34" cy="15" r="2.6">
          <animate
            attributeName="r"
            values="3.2;2.2;3.2"
            dur={speed}
            repeatCount="indefinite"
          />
        </circle>
        <circle cx="13" cy="31" r="2.4">
          <animate
            attributeName="r"
            values="2.2;3.2;2.2"
            dur={speed}
            begin="0.3s"
            repeatCount="indefinite"
          />
        </circle>
        <circle cx="33" cy="33" r="3">
          <animate
            attributeName="r"
            values="3.4;2.4;3.4"
            dur={speed}
            begin="0.6s"
            repeatCount="indefinite"
          />
        </circle>
      </g>

      {/* core */}
      <circle cx="24" cy="24" r="5" fill="#ffffff">
        <animate
          attributeName="r"
          values="4.4;5.4;4.4"
          dur={speed}
          repeatCount="indefinite"
        />
      </circle>
    </svg>
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

function AnswerPanel({ answer }: { answer: AskResponse }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
        <p className="mb-2 text-xs text-slate-500">
          You asked: {answer.question}
        </p>

        {answer.has_recorded_memory ? (
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-200">
            {answer.answer}
          </p>
        ) : (
          /* Deliberately distinct: "no record" is an honest answer,
             not a failed search. */
          <div className="rounded-md border border-amber-900/60 bg-amber-950/20 p-3">
            <p className="text-sm text-amber-200">{answer.answer}</p>
          </div>
        )}
      </div>

      {answer.general_knowledge && (
        <div className="rounded-lg border border-slate-800 p-4">
          <p className="mb-1 text-[10px] uppercase tracking-wider text-slate-600">
            General knowledge — not your history
          </p>
          <p className="text-xs leading-relaxed text-slate-400">
            {answer.general_knowledge}
          </p>
        </div>
      )}

      <p className="text-[10px] text-slate-600">
        Provider: {answer.provider}
        {!answer.provider_available && " (unavailable — used rules)"} ·{" "}
        {answer.sources.length} source
        {answer.sources.length === 1 ? "" : "s"}
      </p>
    </div>
  );
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