"use client";

import { useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!password) return;
    setBusy(true);
    setError(null);
    try {
      await login(password);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 text-slate-200">
      <form
        onSubmit={handleSubmit}
        className="animate-fade-up w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.03] p-7 shadow-2xl shadow-black/40 backdrop-blur-xl"
      >
        <div className="bg-brand mb-5 flex h-11 w-11 items-center justify-center rounded-xl text-lg">🧠</div>
        <h1 className="font-display text-3xl text-white">My Work Memory</h1>
        <p className="mt-1.5 text-sm text-slate-500">Private by design. Enter your password to continue.</p>

        <input
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="mt-6 h-11 w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400/50 focus:ring-4 focus:ring-indigo-500/10"
        />

        {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}

        <button
          type="submit"
          disabled={busy || !password}
          className="bg-brand mt-5 h-11 w-full rounded-xl text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:brightness-110 disabled:opacity-40"
        >
          {busy ? "Checking…" : "Log in"}
        </button>

        <p className="mt-5 text-center text-[11px] text-slate-600">
          5 wrong attempts locks login for 5 minutes.
        </p>
      </form>
    </main>
  );
}