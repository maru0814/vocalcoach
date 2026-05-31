"use client";

import { useState } from "react";

// フェーズは「強制ステップ」ではなく「現在地を示す軽いラベル」。
// 対話駆動フローでは、診断後は練習・歌い直し・質問を自由に行き来できる。
function statusOf(phase: string): { icon: string; label: string; cls: string } {
  if (phase === "done") {
    return { icon: "✅", label: "ひと区切り", cls: "bg-emerald-100 text-emerald-700" };
  }
  if (phase === "A") {
    return { icon: "🔍", label: "弱点さがし", cls: "bg-amber-100 text-amber-700" };
  }
  // practice（診断後のレッスン中）など
  return { icon: "🎯", label: "練習中", cls: "bg-brand-100 text-brand-700" };
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
  const st = statusOf(phase);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const displayTitle = songTitle || "（名称未設定のレッスン）";
  const begin = () => { if (onRename) { setDraft(songTitle || ""); setEditing(true); } };
  const commit = () => { setEditing(false); const n = draft.trim(); if (n && onRename) onRename(n); };

  return (
    <div className="glass border-b border-white/40 px-3 py-2 shadow-sm">
      <div className="flex items-center gap-2">
        {/* レッスン名（クリックで編集） */}
        <span className="shrink-0 text-xs text-slate-400">🎵</span>
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
          <button
            onClick={begin}
            className="group flex min-w-0 flex-1 items-center gap-1 truncate text-left text-xs text-slate-600 hover:text-brand-600"
            title="クリックで名前を変更"
          >
            <span className="truncate">{displayTitle}</span>
            {onRename && <span className="shrink-0 opacity-0 transition group-hover:opacity-100">✏️</span>}
          </button>
        )}

        {/* 現在地ラベル（進行を縛らない） */}
        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${st.cls}`}>
          {st.icon} {st.label}
        </span>
      </div>
    </div>
  );
}
