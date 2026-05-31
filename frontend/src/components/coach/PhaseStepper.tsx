"use client";

import { useState } from "react";

const PHASES: { key: string; label: string; icon: string }[] = [
  { key: "A", label: "曲指定", icon: "🎵" },
  { key: "B", label: "課題発見", icon: "🔍" },
  { key: "C", label: "基礎練", icon: "🎯" },
  { key: "D", label: "練習確認", icon: "✅" },
  { key: "E", label: "再録音", icon: "📈" },
];

export function PhaseStepper({
  phase,
  songTitle,
  onRename,
}: {
  phase: string;
  songTitle?: string | null;
  onRename?: (name: string) => void;
}) {
  const order = ["A", "B", "C", "D", "E", "done"];
  const currentIdx = order.indexOf(phase);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const displayTitle = songTitle || "（名称未設定のレッスン）";

  function begin() {
    if (!onRename) return;
    setDraft(songTitle || "");
    setEditing(true);
  }
  function commit() {
    setEditing(false);
    const name = draft.trim();
    if (name && onRename) onRename(name);
  }

  return (
    <div className="glass border-b border-white/40 px-3 pb-2.5 pt-2 shadow-sm">
      <div className="mb-2 flex items-center gap-1.5 px-1 text-xs text-slate-500">
        <span>🎵</span>
        {editing ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") setEditing(false);
            }}
            placeholder="レッスン名"
            className="min-w-0 flex-1 rounded-md border border-brand-300 bg-white px-2 py-0.5 text-xs outline-none focus:shadow-glow"
            maxLength={200}
          />
        ) : (
          <button
            onClick={begin}
            className="group flex min-w-0 items-center gap-1 truncate text-left hover:text-brand-600"
            title="クリックで名前を変更"
          >
            <span className="truncate">{displayTitle}</span>
            {onRename && <span className="shrink-0 opacity-0 transition group-hover:opacity-100">✏️</span>}
          </button>
        )}
      </div>
      <div className="flex items-center">
        {PHASES.map((p, i) => {
          const done = currentIdx > i || phase === "done";
          const active = phase === p.key;
          return (
            <div key={p.key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-sm transition ${
                    active
                      ? "bg-brand-gradient text-white shadow-soft ring-2 ring-brand-200"
                      : done
                        ? "bg-emerald-100 text-emerald-600"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {done && !active ? "✓" : p.icon}
                </div>
                <span
                  className={`text-[10px] font-medium ${
                    active ? "text-brand-700" : done ? "text-emerald-600" : "text-slate-400"
                  }`}
                >
                  {p.label}
                </span>
              </div>
              {i < PHASES.length - 1 && (
                <div className={`mb-4 h-0.5 flex-1 rounded-full ${done ? "bg-emerald-200" : "bg-slate-200"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
