"use client";

import { useState } from "react";

// 準備ブロック（一度きり）と 練習ループ（繰り返し）
const PREP = [
  { key: "A", label: "曲指定", icon: "🎵" },
  { key: "B", label: "課題発見", icon: "🔍" },
];
const LOOP = [
  { key: "C", label: "基礎練", icon: "🎯" },
  { key: "D", label: "練習確認", icon: "✅" },
  { key: "E", label: "再録音", icon: "📈" },
];

const ORDER = ["A", "B", "C", "D", "E", "done"];

function Dot({ st, icon, label }: { st: "active" | "done" | "todo"; icon: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full text-sm transition ${
          st === "active"
            ? "bg-brand-gradient text-white shadow-soft ring-2 ring-brand-200"
            : st === "done"
              ? "bg-emerald-100 text-emerald-600"
              : "bg-slate-100 text-slate-400"
        }`}
      >
        {st === "done" ? "✓" : icon}
      </div>
      <span
        className={`text-[10px] font-medium ${
          st === "active" ? "text-brand-700" : st === "done" ? "text-emerald-600" : "text-slate-400"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

export function PhaseStepper({
  phase,
  songTitle,
  onRename,
}: {
  phase: string;
  songTitle?: string | null;
  onRename?: (name: string) => void;
}) {
  const idx = ORDER.indexOf(phase);
  const inLoop = ["C", "D", "E"].includes(phase) || phase === "done";

  const stateOf = (key: string): "active" | "done" | "todo" => {
    if (phase === key) return "active";
    if (ORDER.indexOf(key) < idx || phase === "done") return "done";
    return "todo";
  };

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const displayTitle = songTitle || "（名称未設定のレッスン）";
  const begin = () => { if (onRename) { setDraft(songTitle || ""); setEditing(true); } };
  const commit = () => { setEditing(false); const n = draft.trim(); if (n && onRename) onRename(n); };

  return (
    <div className="glass border-b border-white/40 px-3 pb-2.5 pt-2 shadow-sm">
      <div className="mb-2 flex items-center gap-1.5 px-1 text-xs text-slate-500">
        <span>🎵</span>
        {editing ? (
          <input
            autoFocus value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
            placeholder="レッスン名"
            className="min-w-0 flex-1 rounded-md border border-brand-300 bg-white px-2 py-0.5 text-xs outline-none focus:shadow-glow"
            maxLength={200}
          />
        ) : (
          <button onClick={begin} className="group flex min-w-0 items-center gap-1 truncate text-left hover:text-brand-600" title="クリックで名前を変更">
            <span className="truncate">{displayTitle}</span>
            {onRename && <span className="shrink-0 opacity-0 transition group-hover:opacity-100">✏️</span>}
          </button>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        {/* 準備ブロック */}
        {PREP.map((p, i) => (
          <div key={p.key} className="flex items-center gap-1.5">
            <Dot st={stateOf(p.key)} icon={p.icon} label={p.label} />
            <div className={`mb-4 h-0.5 w-4 rounded-full ${stateOf(p.key) === "done" ? "bg-emerald-200" : "bg-slate-200"}`} />
          </div>
        ))}

        {/* 練習ループ（繰り返しブロック） */}
        <div
          className={`relative flex items-center gap-1.5 rounded-2xl border px-2 pb-1 pt-1.5 ${
            inLoop ? "border-brand-200 bg-brand-50/50" : "border-slate-200 bg-slate-50/50"
          }`}
        >
          <span className="absolute -top-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-white px-1.5 text-[9px] font-bold text-brand-600 shadow-sm">
            ↻ 練習ループ
          </span>
          {LOOP.map((p, i) => (
            <div key={p.key} className="flex items-center gap-1.5">
              <Dot st={stateOf(p.key)} icon={p.icon} label={p.label} />
              {i < LOOP.length - 1 && <div className="mb-4 h-0.5 w-4 rounded-full bg-slate-200" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
