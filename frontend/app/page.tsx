export default function Home() {
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
          <NavItem label="📅 Today" count={0} />
          <NavItem label="📅 Yesterday" count={0} />
          <NavItem label="📅 This Week" count={0} />
          <NavItem label="📅 This Month" count={0} />

          <SectionLabel text="PROJECTS / TOPICS" />
          <p className="px-2 text-xs text-slate-600">No topics yet</p>

          <SectionLabel text="TYPES" />
          <NavItem label="📝 Notes" count={0} />
          <NavItem label="🖼️ Screenshots" count={0} />
          <NavItem label="📄 Documents" count={0} />
          <NavItem label="💻 Code Snippets" count={0} />
          <NavItem label="🎤 Meetings" count={0} />
        </aside>

        {/* CENTER */}
        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="border-b border-slate-800 px-6 py-4">
            <h2 className="text-lg font-semibold text-white">Chat</h2>
            <p className="text-xs text-slate-500">
              Ask about your work, find past solutions, learn, or add new memories.
            </p>
          </div>

          <div className="flex flex-1 items-center justify-center overflow-y-auto p-6">
            <div className="text-center">
              <div className="mb-3 text-4xl">🧠</div>
              <p className="text-sm text-slate-400">
                Your memory is empty.
              </p>
              <p className="mt-1 text-xs text-slate-600">
                Tell me what you worked on today and I&apos;ll remember it.
              </p>
            </div>
          </div>

          <div className="border-t border-slate-800 p-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <textarea
                rows={2}
                placeholder="Ask anything, or add a new memory..."
                className="w-full resize-none bg-transparent text-sm placeholder-slate-500 outline-none"
              />
              <div className="mt-2 flex items-center gap-2">
                <Chip label="📎 Attach" />
                <Chip label="🖼️ Screenshot" />
                <Chip label="🎤 Voice" />
                <button className="ml-auto rounded-lg bg-indigo-600 px-4 py-1.5 text-sm text-white">
                  Send
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT */}
        <aside className="w-80 shrink-0 overflow-y-auto border-l border-slate-800 p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Related Memory</h3>
          <div className="rounded-lg border border-slate-800 p-4 text-center">
            <p className="text-xs text-slate-500">
              Related memories will appear here as you chat.
            </p>
          </div>

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

/* ---------- small building blocks ---------- */

function NavItem({ label, count }: { label: string; count?: number }) {
  return (
    <div className="flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800/60">
      <span>{label}</span>
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