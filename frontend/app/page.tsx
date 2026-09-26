"use client";

import { createElement, useEffect, useMemo, useRef, useState } from "react";
import {
  askQuestion,
  attachmentUrl,
  captureMemory,
  getTopicHistory,
  listMemories,
  uploadAttachment,
  type AskResponse,
  type AttachmentBrief,
  type CapturePreview,
  type Memory,
  type TopicHistory,
} from "@/lib/api";

/* ============================================================
   Constants
   ============================================================ */

type TypeMeta = { label: string; section: string; icon: string; tone: string };

const TYPE_META: Record<string, TypeMeta> = {
  incident: {
    label: "Incident",
    section: "Problems I hit",
    icon: "⚠️",
    tone: "bg-orange-500/10 text-orange-300 ring-orange-400/20",
  },
  mistake: {
    label: "Mistake",
    section: "Mistakes",
    icon: "✖️",
    tone: "bg-rose-500/10 text-rose-300 ring-rose-400/20",
  },
  solution: {
    label: "Solution",
    section: "Solutions",
    icon: "✅",
    tone: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/20",
  },
  learning: {
    label: "Learning",
    section: "What I learned",
    icon: "🧠",
    tone: "bg-sky-500/10 text-sky-300 ring-sky-400/20",
  },
  code: {
    label: "Code",
    section: "Code",
    icon: "💻",
    tone: "bg-violet-500/10 text-violet-300 ring-violet-400/20",
  },
  meeting: {
    label: "Meeting",
    section: "Meetings",
    icon: "🎤",
    tone: "bg-amber-500/10 text-amber-300 ring-amber-400/20",
  },
  note: {
    label: "Note",
    section: "Notes",
    icon: "📝",
    tone: "bg-slate-500/10 text-slate-300 ring-slate-400/20",
  },
};

const TYPE_ORDER = ["incident", "mistake", "solution", "learning", "code", "meeting", "note"];

const SOURCE_LABELS: Record<string, string> = {
  user_typed: "Typed by you",
  user_voice: "Spoken by you",
  screenshot: "Screenshot",
  document: "File",
  notebook_photo: "Notebook photo",
  meeting_transcript: "Meeting transcript",
};

const FILE_ICONS: Record<string, string> = {
  screenshot: "🖼️",
  image: "🖼️",
  notebook_photo: "📓",
  document: "📄",
  code: "💻",
};

// What the Attach picker offers. The backend makes the final decision
// and refuses anything that looks like a credentials file.
const FILE_ACCEPT =
  "image/*,.pdf,.txt,.md,.docx,.py,.yaml,.yml,.tf,.tfvars,.hcl,.json,.sh,.toml,.ini,.conf,.js,.ts,.go,.sql,.xml";

const EXAMPLES = [
  "Fixed an ArgoCD sync failure — the Helm values were wrong, corrected values.yaml and re-synced.",
  "Investigated a pod in CrashLoopBackOff with K9s. Found a missing env var in the deployment.",
  "I think I changed the Workload Identity binding, but I'm not sure that was the fix.",
];

type Filter = "all" | "today" | "week" | "files" | `type:${string}`;

/* ============================================================
   Page
   ============================================================ */

export default function Home() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [topic, setTopic] = useState<TopicHistory | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [saving, setSaving] = useState(false);
  const [asking, setAsking] = useState(false);
  const [openingTopic, setOpeningTopic] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastPreview, setLastPreview] = useState<CapturePreview | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const composerRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listMemories()
      .then(setMemories)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Local preview for a pending image, released when no longer needed.
  useEffect(() => {
    if (!pendingFile || !pendingFile.type.startsWith("image/")) {
      setPendingPreview(null);
      return;
    }
    const url = URL.createObjectURL(pendingFile);
    setPendingPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  const today = localISO(new Date());
  const weekStart = localISO(new Date(Date.now() - 6 * 864e5));

  const counts = useMemo(() => {
    const byType: Record<string, number> = {};
    let todayCount = 0;
    let weekCount = 0;
    let filesCount = 0;
    for (const m of memories) {
      byType[m.memory_type] = (byType[m.memory_type] ?? 0) + 1;
      if (m.occurred_on === today) todayCount++;
      if (m.occurred_on >= weekStart) weekCount++;
      if ((m.attachments ?? []).length > 0) filesCount++;
    }
    return { byType, today: todayCount, week: weekCount, files: filesCount };
  }, [memories, today, weekStart]);

  const topics = useMemo(() => topicCounts(memories), [memories]);

  const visible = useMemo(
    () =>
      memories.filter((m) => {
        if (filter === "all") return true;
        if (filter === "today") return m.occurred_on === today;
        if (filter === "week") return m.occurred_on >= weekStart;
        if (filter === "files") return (m.attachments ?? []).length > 0;
        return m.memory_type === filter.slice(5);
      }),
    [memories, filter, today, weekStart]
  );

  const mode: "feed" | "answer" | "topic" = topic ? "topic" : answer ? "answer" : "feed";

  function showFeed(f: Filter) {
    setAnswer(null);
    setTopic(null);
    setFilter(f);
  }

  function pickFile(file: File | null) {
    setError(null);
    setPendingFile(file);
    if (file) composerRef.current?.focus();
  }

  async function openTopic(t: string) {
    setOpeningTopic(t);
    setError(null);
    try {
      const history = await getTopicHistory(t);
      setAnswer(null);
      setTopic(history);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load topic");
    } finally {
      setOpeningTopic(null);
    }
  }

  async function handleSave() {
    const text = input.trim();
    if (!text && !pendingFile) return;
    setSaving(true);
    setError(null);
    try {
      if (pendingFile) {
        // The file is stored as evidence; the note (if any) becomes
        // an AI-structured memory alongside it.
        const { memory } = await uploadAttachment(pendingFile, text);
        setMemories((prev) => [memory, ...prev]);
        setPendingFile(null);
        setLastPreview(null);
      } else {
        const { memory, preview } = await captureMemory(text);
        setMemories((prev) => [memory, ...prev]);
        setLastPreview(preview);
      }
      setInput("");
      showFeed("all");
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
      const result = await askQuestion(q);
      setTopic(null);
      setAnswer(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setAsking(false);
    }
  }

  const eyebrow = mode === "topic" ? "Topic history" : mode === "answer" ? "Answer" : "My work memory";

  const title =
    mode === "topic" ? `#${topic!.topic}` : mode === "answer" ? answer!.question : filterLabel(filter);

  const subtitle =
    mode === "topic"
      ? "Everything you recorded about this topic, across time."
      : mode === "answer"
      ? "Answered only from what you recorded."
      : loading
      ? "Loading your memories…"
      : `${visible.length} ${visible.length === 1 ? "memory" : "memories"}`;

  return (
    <div className="flex h-screen flex-col text-slate-200">
      {/* ======================= HEADER ======================= */}
      <header className="flex h-16 shrink-0 items-center gap-4 border-b border-white/5 bg-[#070a14]/60 px-5 backdrop-blur-xl">
        <button onClick={() => showFeed("all")} className="flex shrink-0 items-center gap-3">
          <MemoryLogo active={asking || saving || !!openingTopic} />
          <div className="hidden text-left sm:block">
            <h1 className="text-[15px] font-semibold tracking-tight text-white">My Work Memory</h1>
            <p className="text-[11px] text-slate-500">Remember. Learn. Grow.</p>
          </div>
        </button>

        <div className="mx-auto w-full max-w-2xl">
          <div className="group relative flex items-center">
            <SearchIcon className="pointer-events-none absolute left-4 h-4 w-4 text-slate-500 transition group-focus-within:text-indigo-300" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAsk()}
              placeholder="Ask your memory — e.g. How did I fix the ArgoCD sync issue?"
              className="h-11 w-full rounded-full border border-white/10 bg-white/[0.03] pl-11 pr-28 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400/50 focus:bg-white/[0.05] focus:ring-4 focus:ring-indigo-500/10"
            />
            <button
              onClick={handleAsk}
              disabled={asking || !question.trim()}
              className="bg-brand absolute right-1.5 h-8 rounded-full px-4 text-xs font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:brightness-110 disabled:opacity-40"
            >
              {asking ? "Thinking…" : "Ask"}
            </button>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden rounded-full border border-white/10 px-2.5 py-1 text-[11px] font-medium text-slate-400 sm:block">
            EN
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-xs font-semibold text-white ring-2 ring-white/10">
            SR
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ======================= LEFT ======================= */}
        <aside className="hidden w-60 shrink-0 flex-col overflow-y-auto border-r border-white/5 px-3 py-4 md:flex lg:w-64">
          <button
            onClick={() => {
              showFeed("all");
              composerRef.current?.focus();
            }}
            className="bg-brand mb-5 flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:brightness-110"
          >
            <span className="text-base leading-none">＋</span> New memory
          </button>

          <SidebarItem icon="🕐" label="Reconstruct my day" badge="Soon" />

          <SectionLabel text="My memory" />
          <SidebarItem
            icon="📚"
            label="All memories"
            count={memories.length}
            active={mode === "feed" && filter === "all"}
            onClick={() => showFeed("all")}
          />
          <SidebarItem
            icon="☀️"
            label="Today"
            count={counts.today}
            active={mode === "feed" && filter === "today"}
            onClick={() => showFeed("today")}
          />
          <SidebarItem
            icon="🗓️"
            label="This week"
            count={counts.week}
            active={mode === "feed" && filter === "week"}
            onClick={() => showFeed("week")}
          />
          <SidebarItem
            icon="📎"
            label="With files"
            count={counts.files}
            active={mode === "feed" && filter === "files"}
            onClick={() => showFeed("files")}
          />

          <SectionLabel text="Topics" />
          {topics.length === 0 ? (
            <p className="px-2.5 text-xs text-slate-600">Topics appear as you record memories.</p>
          ) : (
            topics.map(([t, n]) => (
              <SidebarItem
                key={t}
                icon="#"
                label={t}
                count={n}
                active={topic?.topic === t}
                loading={openingTopic === t}
                onClick={() => openTopic(t)}
              />
            ))
          )}

          {Object.keys(counts.byType).length > 0 && (
            <>
              <SectionLabel text="Types" />
              {TYPE_ORDER.filter((t) => counts.byType[t]).map((t) => (
                <SidebarItem
                  key={t}
                  icon={meta(t).icon}
                  label={meta(t).section}
                  count={counts.byType[t]}
                  active={mode === "feed" && filter === `type:${t}`}
                  onClick={() => showFeed(`type:${t}`)}
                />
              ))}
            </>
          )}

          <div className="mt-auto pt-6">
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <p className="flex items-center gap-1.5 text-[11px] font-medium text-slate-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Private by design
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                Stored in your own database. Never invents your history.
              </p>
            </div>
          </div>
        </aside>

        {/* ======================= CENTER ======================= */}
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="px-8 pb-4 pt-7">
            <div className="mx-auto flex max-w-3xl items-end justify-between gap-4">
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-indigo-300/70">{eyebrow}</p>
                <h2 className="font-display mt-1 truncate text-3xl text-white">{title}</h2>
                <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
              </div>
              {mode !== "feed" && (
                <button
                  onClick={() => showFeed(filter)}
                  className="shrink-0 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition hover:border-white/20 hover:text-slate-200"
                >
                  ← Back to memories
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-8 pb-6">
            <div className="mx-auto max-w-3xl">
              {mode === "topic" ? (
                <TopicView history={topic!} onOpenTopic={openTopic} />
              ) : mode === "answer" ? (
                <AnswerView answer={answer!} onOpenTopic={openTopic} />
              ) : (
                <FeedView
                  memories={visible}
                  loading={loading}
                  filter={filter}
                  onOpenTopic={openTopic}
                  onExample={(text) => {
                    setInput(text);
                    composerRef.current?.focus();
                  }}
                />
              )}
            </div>
          </div>

          {/* composer */}
          <div className="px-8 pb-6">
            <div className="mx-auto max-w-3xl">
              {error && (
                <div className="mb-3 flex items-start justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/[0.06] px-4 py-2.5 text-xs text-rose-200">
                  <span>{error}</span>
                  <button onClick={() => setError(null)} className="text-rose-300/70 hover:text-rose-200">
                    ✕
                  </button>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                hidden
                accept={FILE_ACCEPT}
                onChange={(e) => {
                  pickFile(e.target.files?.[0] ?? null);
                  e.target.value = "";
                }}
              />
              <input
                ref={imageInputRef}
                type="file"
                hidden
                accept="image/*"
                onChange={(e) => {
                  pickFile(e.target.files?.[0] ?? null);
                  e.target.value = "";
                }}
              />

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  const dropped = e.dataTransfer.files?.[0];
                  if (dropped) pickFile(dropped);
                }}
                className={`rounded-2xl border bg-white/[0.03] p-3 shadow-2xl shadow-black/40 backdrop-blur-xl transition focus-within:border-indigo-400/40 focus-within:ring-4 focus-within:ring-indigo-500/10 ${
                  dragOver ? "border-indigo-400/60 ring-4 ring-indigo-500/20" : "border-white/10"
                }`}
              >
                {pendingFile && (
                  <div className="mb-2 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-2">
                    {pendingPreview ? (
                      <Picture src={pendingPreview} alt="" className="h-12 w-16 rounded-md object-cover" />
                    ) : (
                      <span className="flex h-12 w-12 items-center justify-center rounded-md bg-white/5 text-lg">
                        📄
                      </span>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs text-slate-200">{pendingFile.name}</p>
                      <p className="text-[10px] text-slate-500">
                        {formatBytes(pendingFile.size)} · add a note describing it (optional)
                      </p>
                    </div>
                    <button
                      onClick={() => setPendingFile(null)}
                      className="px-2 text-slate-500 hover:text-slate-200"
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                )}

                <textarea
                  ref={composerRef}
                  rows={2}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      handleSave();
                    }
                  }}
                  onPaste={(e) => {
                    // Pasting a screenshot (Win+Shift+S, then Ctrl+V)
                    // attaches it directly.
                    const pasted = Array.from(e.clipboardData.files).find((f) => f.type.startsWith("image/"));
                    if (pasted) {
                      e.preventDefault();
                      pickFile(new File([pasted], `screenshot-${Date.now()}.png`, { type: pasted.type }));
                    }
                  }}
                  placeholder={
                    pendingFile
                      ? "Describe this file (optional) — e.g. K9s showing the pod in CrashLoopBackOff"
                      : "What did you work on? Describe it naturally — or paste a screenshot."
                  }
                  className="w-full resize-none bg-transparent px-2 pt-1 text-sm leading-relaxed text-slate-100 outline-none placeholder:text-slate-500"
                />
                <div className="mt-2 flex items-center gap-1.5">
                  <ComposerButton icon="📎" label="Attach" onClick={() => fileInputRef.current?.click()} />
                  <ComposerButton icon="🖼️" label="Screenshot" onClick={() => imageInputRef.current?.click()} />
                  <ComposerButton icon="🎙️" label="Voice" soon />
                  <span className="ml-auto hidden text-[11px] text-slate-600 sm:inline">Ctrl + Enter to save</span>
                  <button
                    onClick={handleSave}
                    disabled={saving || (!input.trim() && !pendingFile)}
                    className="bg-brand ml-auto rounded-xl px-4 py-2 text-xs font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:brightness-110 disabled:opacity-40 sm:ml-2"
                  >
                    {saving ? "Saving…" : pendingFile ? "Save with file" : "Save memory"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>

        {/* ======================= RIGHT ======================= */}
        <aside className="hidden w-72 shrink-0 flex-col gap-4 overflow-y-auto border-l border-white/5 p-4 lg:flex xl:w-80">
          {mode === "topic" ? (
            <Panel title="Related topics" subtitle="Tagged alongside this one">
              <RelatedTopics history={topic!} onOpenTopic={openTopic} />
            </Panel>
          ) : mode === "answer" ? (
            <Panel title="About this answer">
              <AnswerInfo answer={answer!} />
            </Panel>
          ) : lastPreview ? (
            <Panel title="What the AI understood" subtitle="From your last saved memory">
              <PreviewPanel preview={lastPreview} />
            </Panel>
          ) : (
            <Panel title="How it works">
              <HowItWorks />
            </Panel>
          )}

          <Panel title="Studio" subtitle="Create outputs from your memory">
            <div className="grid grid-cols-2 gap-2">
              <StudioCard icon="📝" label="Summary" />
              <StudioCard icon="🗺️" label="Mind map" />
              <StudioCard icon="📚" label="Learn more" />
              <StudioCard icon="🗓️" label="Timeline" />
            </div>
          </Panel>

          <Panel title="More">
            <div className="space-y-1">
              <MoreItem icon="🎯" label="Learning gaps" hint="Topics to explore" />
              <MoreItem icon="🎤" label="Interview mode" hint="Practice on your real work" />
              <MoreItem icon="🕸️" label="Knowledge map" hint="How topics connect" />
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  );
}

/* ============================================================
   Center views
   ============================================================ */

type FeedViewProps = {
  memories: Memory[];
  loading: boolean;
  filter: Filter;
  onOpenTopic: (t: string) => void;
  onExample: (text: string) => void;
};

function FeedView({ memories, loading, filter, onOpenTopic, onExample }: FeedViewProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-2xl border border-white/[0.04] bg-white/[0.02]" />
        ))}
      </div>
    );
  }

  if (memories.length === 0) {
    if (filter !== "all") {
      return (
        <div className="animate-fade-up rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 text-center">
          <p className="text-sm text-slate-400">Nothing recorded for {filterLabel(filter).toLowerCase()} yet.</p>
        </div>
      );
    }
    return (
      <div className="animate-fade-up flex flex-col items-center py-12 text-center">
        <MemoryLogo size={64} active />
        <h3 className="font-display mt-5 text-2xl text-white">Your memory is empty</h3>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Describe what you worked on in your own words. I&apos;ll organise it — and I&apos;ll never invent
          anything you didn&apos;t say.
        </p>
        <div className="mt-6 w-full max-w-lg space-y-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => onExample(ex)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-left text-xs leading-relaxed text-slate-400 transition hover:border-indigo-400/30 hover:text-slate-200"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {groupByDate(memories).map(([date, items]) => (
        <section key={date} className="animate-fade-up">
          <div className="mb-3 flex items-center gap-3">
            <h3 className="text-xs font-medium text-slate-400">{prettyDate(date)}</h3>
            <div className="h-px flex-1 bg-white/5" />
            <span className="text-[11px] tabular-nums text-slate-600">{items.length}</span>
          </div>
          <div className="space-y-3">
            {items.map((m) => (
              <MemoryCard key={m.id} memory={m} onOpenTopic={onOpenTopic} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

type AnswerViewProps = {
  answer: AskResponse;
  onOpenTopic: (t: string) => void;
};

function AnswerView({ answer, onOpenTopic }: AnswerViewProps) {
  return (
    <div className="animate-fade-up space-y-5">
      {answer.has_recorded_memory ? (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6">
          <p className="mb-3 flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-emerald-300/80">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            From your recorded memory
          </p>
          <p className="whitespace-pre-line text-[15px] leading-relaxed text-slate-200">{answer.answer}</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-amber-400/20 bg-amber-500/[0.06] p-6">
          <p className="mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-amber-300/90">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            No recorded memory
          </p>
          <p className="text-[15px] leading-relaxed text-amber-100/90">{answer.answer}</p>
        </div>
      )}

      {answer.general_knowledge && (
        <div className="rounded-2xl border border-dashed border-white/10 p-5">
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
            General knowledge — not your history
          </p>
          <p className="text-sm leading-relaxed text-slate-400">{answer.general_knowledge}</p>
        </div>
      )}

      {answer.sources.length > 0 && (
        <div>
          <h3 className="mb-3 text-xs font-medium text-slate-400">
            Based on {answer.sources.length} {answer.sources.length === 1 ? "memory" : "memories"}
          </h3>
          <div className="space-y-3">
            {answer.sources.map((m) => (
              <MemoryCard key={m.id} memory={m} onOpenTopic={onOpenTopic} showDate />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

type TopicViewProps = {
  history: TopicHistory;
  onOpenTopic: (t: string) => void;
};

function TopicView({ history, onOpenTopic }: TopicViewProps) {
  if (history.total === 0) {
    return (
      <div className="animate-fade-up rounded-2xl border border-amber-400/20 bg-amber-500/[0.06] p-6">
        <p className="text-[15px] text-amber-100/90">You have no recorded memories about #{history.topic}.</p>
      </div>
    );
  }

  const sections = [
    ...TYPE_ORDER.filter((t) => history.by_type[t]?.length),
    ...Object.keys(history.by_type).filter((t) => !TYPE_ORDER.includes(t)),
  ];

  return (
    <div className="animate-fade-up space-y-8">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Memories" value={String(history.total)} />
        <StatCard label="First recorded" value={shortDate(history.first_seen)} />
        <StatCard label="Most recent" value={shortDate(history.last_seen)} />
        <StatCard label="Unconfirmed" value={String(history.uncertain_count)} warn={history.uncertain_count > 0} />
      </div>

      {history.uncertain_count > 0 && (
        <p className="rounded-xl border border-amber-400/15 bg-amber-500/[0.05] px-4 py-3 text-xs leading-relaxed text-amber-200/90">
          {history.uncertain_count} of these {history.total} memories were recorded with uncertainty. Treat that
          part of this history as unconfirmed.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {sections.map((t) => (
          <span
            key={t}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs ring-1 ring-inset ${meta(t).tone}`}
          >
            {meta(t).icon} {meta(t).section}
            <span className="opacity-60">{history.by_type[t].length}</span>
          </span>
        ))}
      </div>

      {sections.map((t) => (
        <section key={t}>
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
            <span>{meta(t).icon}</span>
            {meta(t).section}
            <span className="text-xs font-normal text-slate-500">{history.by_type[t].length}</span>
          </h3>
          <ol className="relative space-y-5 border-l border-white/10 pl-6">
            {history.by_type[t].map((m) => (
              <li key={m.id} className="relative">
                <span className="absolute -left-[29px] top-1 h-2.5 w-2.5 rounded-full border-2 border-[#070a14] bg-indigo-400" />
                <p className="text-[11px] text-slate-500">{shortDate(m.occurred_on)}</p>
                <div className="mt-1.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium leading-snug text-slate-100">{m.title}</p>
                    {m.confidence === "uncertain" && <UncertainBadge />}
                  </div>
                  {titleDiffers(m) && <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{m.content}</p>}
                  <AttachmentList items={m.attachments ?? []} />
                  <TopicChips topics={m.topics.filter((x) => x !== history.topic)} onOpenTopic={onOpenTopic} />
                </div>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

/* ============================================================
   Right-panel content
   ============================================================ */

function RelatedTopics({ history, onOpenTopic }: TopicViewProps) {
  if (history.related_topics.length === 0) {
    return <p className="text-xs text-slate-500">No related topics yet.</p>;
  }
  const max = Math.max(...history.related_topics.map((r) => r.shared_memories));
  return (
    <div className="space-y-2">
      {history.related_topics.map((r) => (
        <button key={r.topic} onClick={() => onOpenTopic(r.topic)} className="group block w-full text-left">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-300 group-hover:text-white">#{r.topic}</span>
            <span className="tabular-nums text-slate-500">{r.shared_memories}</span>
          </div>
          <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/5">
            <div className="bg-brand h-full rounded-full" style={{ width: `${(r.shared_memories / max) * 100}%` }} />
          </div>
        </button>
      ))}
      <p className="pt-2 text-[10px] leading-relaxed text-slate-600">Derived from your own tags — not guessed by AI.</p>
    </div>
  );
}

function AnswerInfo({ answer }: { answer: AskResponse }) {
  return (
    <div className="space-y-3 text-xs">
      <InfoRow label="Recorded memory found" value={answer.has_recorded_memory ? "Yes" : "No"} />
      <InfoRow label="Sources used" value={String(answer.sources.length)} />
      <InfoRow label="Provider" value={`${answer.provider}${answer.provider_available ? "" : " (rules)"}`} />
      <p className="border-t border-white/5 pt-3 text-[11px] leading-relaxed text-slate-500">
        Answers use only memories you recorded. General knowledge is always labelled separately, and never
        presented as your experience.
      </p>
    </div>
  );
}

function PreviewPanel({ preview }: { preview: CapturePreview }) {
  return (
    <div className="space-y-3">
      <InfoBlock label="Title" value={preview.title} />
      <div className="flex gap-2">
        <TypeBadge type={preview.memory_type} />
        {preview.confidence === "uncertain" && <UncertainBadge />}
      </div>
      {preview.uncertainty_markers.length > 0 && (
        <p className="text-[11px] text-amber-300/80">
          Marked unconfirmed because you said &ldquo;{preview.uncertainty_markers.join('", "')}&rdquo;.
        </p>
      )}
      {preview.topics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {preview.topics.map((t) => (
            <span key={t} className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-300">
              #{t}
            </span>
          ))}
        </div>
      )}
      <p className="border-t border-white/5 pt-3 text-[10px] leading-relaxed text-slate-600">
        Title, type and topics are AI interpretation. Your original words are stored unchanged. Provider:{" "}
        {preview.provider}.
      </p>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    ["✍️", "Describe your work", "In your own words — no forms."],
    ["📎", "Attach evidence", "Paste a screenshot or drop a file. Originals are kept."],
    ["🧩", "It gets organised", "Type, topics and uncertainty are extracted."],
    ["🔎", "Ask anytime", "Answers come only from what you recorded."],
  ];
  return (
    <ol className="space-y-3">
      {steps.map(([icon, head, body]) => (
        <li key={head} className="flex gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/5 text-sm">{icon}</span>
          <div>
            <p className="text-xs font-medium text-slate-200">{head}</p>
            <p className="text-[11px] text-slate-500">{body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

/* ============================================================
   Building blocks
   ============================================================ */

type MemoryCardProps = {
  memory: Memory;
  onOpenTopic: (t: string) => void;
  showDate?: boolean;
};

function MemoryCard({ memory, onOpenTopic, showDate = false }: MemoryCardProps) {
  return (
    <article className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition hover:border-white/10 hover:bg-white/[0.035]">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <TypeBadge type={memory.memory_type} />
        {memory.confidence === "uncertain" && <UncertainBadge />}
        {showDate && <span className="text-[11px] text-slate-500">{shortDate(memory.occurred_on)}</span>}
        <span className="ml-auto text-[11px] text-slate-600">{sourceLabel(memory)}</span>
      </div>
      <h4 className="text-[15px] font-medium leading-snug text-slate-100">{memory.title}</h4>
      {titleDiffers(memory) && <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{memory.content}</p>}
      <AttachmentList items={memory.attachments ?? []} />
      <TopicChips topics={memory.topics} onOpenTopic={onOpenTopic} />
    </article>
  );
}

function AttachmentList({ items }: { items: AttachmentBrief[] }) {
  if (items.length === 0) return null;
  const images = items.filter((a) => a.content_type.startsWith("image/"));
  const files = items.filter((a) => !a.content_type.startsWith("image/"));

  return (
    <div className="mt-3 space-y-2">
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((a) => (
            <ExternalLink
              key={a.id}
              href={attachmentUrl(a.id)}
              title={`${a.original_filename} — open original`}
              className="group relative block h-24 w-36 overflow-hidden rounded-lg border border-white/10 bg-black/30"
            >
              <Picture
                src={attachmentUrl(a.id)}
                alt={a.original_filename}
                className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
              />
              <span className="absolute inset-x-0 bottom-0 truncate bg-gradient-to-t from-black/80 to-transparent px-2 pb-1 pt-4 text-[10px] text-slate-200">
                {a.original_filename}
              </span>
            </ExternalLink>
          ))}
        </div>
      )}
      {files.map((a) => (
        <ExternalLink
          key={a.id}
          href={attachmentUrl(a.id)}
          className="flex items-center gap-2.5 rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-2 text-xs transition hover:border-indigo-400/30"
        >
          <span>{FILE_ICONS[a.kind] ?? "📄"}</span>
          <span className="min-w-0 flex-1 truncate text-slate-300">{a.original_filename}</span>
          <span className="text-[10px] text-slate-500">{formatBytes(a.size_bytes)}</span>
          <span className="text-[11px] text-indigo-300">Open ↗</span>
        </ExternalLink>
      ))}
    </div>
  );
}

/*
 * Links and images are created in code rather than written as tags,
 * so copying this file can never strip them out.
 */
type ExternalLinkProps = {
  href: string;
  title?: string;
  className?: string;
  children?: React.ReactNode;
};

function ExternalLink({ href, title, className, children }: ExternalLinkProps) {
  return createElement("a", { href, title, className, target: "_blank", rel: "noreferrer" }, children);
}

type PictureProps = { src: string; alt: string; className?: string };

function Picture({ src, alt, className }: PictureProps) {
  return createElement("img", { src, alt, className });
}

type TopicChipsProps = {
  topics: string[];
  onOpenTopic: (t: string) => void;
};

function TopicChips({ topics, onOpenTopic }: TopicChipsProps) {
  if (topics.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {topics.map((t) => (
        <button
          key={t}
          onClick={() => onOpenTopic(t)}
          className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[11px] text-indigo-300 transition hover:bg-indigo-500/20 hover:text-indigo-200"
        >
          #{t}
        </button>
      ))}
    </div>
  );
}

function TypeBadge({ type }: { type: string }) {
  const m = meta(type);
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ring-inset ${m.tone}`}>
      {m.icon} {m.label}
    </span>
  );
}

function UncertainBadge() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-300 ring-1 ring-inset ring-amber-400/20">
      ? Unconfirmed
    </span>
  );
}

type StatCardProps = { label: string; value: string; warn?: boolean };

function StatCard({ label, value, warn = false }: StatCardProps) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-medium ${warn ? "text-amber-300" : "text-slate-100"}`}>{value}</p>
    </div>
  );
}

type SidebarItemProps = {
  icon: string;
  label: string;
  count?: number;
  active?: boolean;
  loading?: boolean;
  badge?: string;
  onClick?: () => void;
};

function SidebarItem({ icon, label, count, active = false, loading = false, badge, onClick }: SidebarItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition disabled:cursor-default ${
        active ? "bg-white/[0.07] text-white" : "text-slate-400 hover:bg-white/[0.03] hover:text-slate-200"
      }`}
    >
      <span className="w-4 text-center text-xs opacity-80">{icon}</span>
      <span className="flex-1 truncate">{label}</span>
      {loading && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />}
      {badge && (
        <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-slate-500">
          {badge}
        </span>
      )}
      {count !== undefined && (
        <span className={`text-[11px] tabular-nums ${active ? "text-indigo-300" : "text-slate-600"}`}>{count}</span>
      )}
    </button>
  );
}

function SectionLabel({ text }: { text: string }) {
  return (
    <p className="mb-1 mt-6 px-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">{text}</p>
  );
}

type PanelProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
};

function Panel({ title, subtitle, children }: PanelProps) {
  return (
    <section className="animate-fade-up rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      {subtitle && <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function StudioCard({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="relative flex flex-col gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
      <span className="text-lg">{icon}</span>
      <span className="text-xs text-slate-300">{label}</span>
      <span className="absolute right-2 top-2 rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-slate-500">
        Soon
      </span>
    </div>
  );
}

type MoreItemProps = { icon: string; label: string; hint: string };

function MoreItem({ icon, label, hint }: MoreItemProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-2 py-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-sm">{icon}</span>
      <div className="flex-1">
        <p className="text-xs text-slate-300">{label}</p>
        <p className="text-[10px] text-slate-600">{hint}</p>
      </div>
      <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-slate-500">
        Soon
      </span>
    </div>
  );
}

type ComposerButtonProps = {
  icon: string;
  label: string;
  onClick?: () => void;
  soon?: boolean;
};

function ComposerButton({ icon, label, onClick, soon = false }: ComposerButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={soon}
      title={soon ? "Coming in a later phase" : label}
      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-white/[0.05] hover:text-slate-200 disabled:cursor-not-allowed disabled:text-slate-600 disabled:hover:bg-transparent"
    >
      <span>{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-200">{value}</span>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-0.5 text-xs leading-relaxed text-slate-200">{value}</p>
    </div>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" strokeLinecap="round" />
    </svg>
  );
}

/* ============================================================
   Logo
   ============================================================ */

function MemoryLogo({ size = 36, active = false }: { size?: number; active?: boolean }) {
  const speed = active ? "0.9s" : "2.8s";
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
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
      <circle cx="24" cy="24" r="16" fill="url(#awmGlow)">
        <animate attributeName="opacity" values="0.25;0.6;0.25" dur={speed} repeatCount="indefinite" />
      </circle>
      <g stroke="#e0e7ff" strokeWidth="1.2" strokeLinecap="round">
        <line x1="24" y1="24" x2="14" y2="14">
          <animate attributeName="opacity" values="0.2;0.85;0.2" dur={speed} repeatCount="indefinite" />
        </line>
        <line x1="24" y1="24" x2="34" y2="15">
          <animate attributeName="opacity" values="0.85;0.2;0.85" dur={speed} repeatCount="indefinite" />
        </line>
        <line x1="24" y1="24" x2="13" y2="31">
          <animate attributeName="opacity" values="0.4;0.9;0.4" dur={speed} begin="0.3s" repeatCount="indefinite" />
        </line>
        <line x1="24" y1="24" x2="33" y2="33">
          <animate attributeName="opacity" values="0.9;0.3;0.9" dur={speed} begin="0.6s" repeatCount="indefinite" />
        </line>
        <line x1="14" y1="14" x2="34" y2="15" opacity="0.3" />
        <line x1="13" y1="31" x2="33" y2="33" opacity="0.3" />
      </g>
      <g fill="#e0e7ff">
        <circle cx="14" cy="14" r="3">
          <animate attributeName="r" values="2.4;3.4;2.4" dur={speed} repeatCount="indefinite" />
        </circle>
        <circle cx="34" cy="15" r="2.6">
          <animate attributeName="r" values="3.2;2.2;3.2" dur={speed} repeatCount="indefinite" />
        </circle>
        <circle cx="13" cy="31" r="2.4">
          <animate attributeName="r" values="2.2;3.2;2.2" dur={speed} begin="0.3s" repeatCount="indefinite" />
        </circle>
        <circle cx="33" cy="33" r="3">
          <animate attributeName="r" values="3.4;2.4;3.4" dur={speed} begin="0.6s" repeatCount="indefinite" />
        </circle>
      </g>
      <circle cx="24" cy="24" r="5" fill="#ffffff">
        <animate attributeName="r" values="4.4;5.4;4.4" dur={speed} repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

/* ============================================================
   Helpers
   ============================================================ */

function meta(type: string): TypeMeta {
  return TYPE_META[type] ?? TYPE_META.note;
}

function filterLabel(f: Filter): string {
  if (f === "all") return "All memories";
  if (f === "today") return "Today";
  if (f === "week") return "This week";
  if (f === "files") return "With files";
  return meta(f.slice(5)).section;
}

function localISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function prettyDate(iso: string): string {
  if (iso === localISO(new Date())) return "Today";
  if (iso === localISO(new Date(Date.now() - 864e5))) return "Yesterday";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function shortDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function titleDiffers(m: Memory): boolean {
  const norm = (s: string) => s.trim().replace(/[.\s]+$/, "").toLowerCase();
  return norm(m.title) !== norm(m.content);
}

function sourceLabel(m: Memory): string {
  const labels = Array.from(new Set(m.evidence.map((e) => SOURCE_LABELS[e.source_type] ?? e.source_type)));
  return labels.length > 0 ? labels.join(" · ") : "No source";
}

function groupByDate(memories: Memory[]): [string, Memory[]][] {
  const map = new Map<string, Memory[]>();
  for (const m of memories) {
    const list = map.get(m.occurred_on) ?? [];
    list.push(m);
    map.set(m.occurred_on, list);
  }
  return [...map.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1));
}

function topicCounts(memories: Memory[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const m of memories) {
    for (const t of m.topics) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}