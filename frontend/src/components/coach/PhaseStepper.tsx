"use client";

const PHASES: { key: string; label: string }[] = [
  { key: "A", label: "曲指定" },
  { key: "B", label: "課題発見" },
  { key: "C", label: "基礎練" },
  { key: "D", label: "練習確認" },
  { key: "E", label: "再録音" },
];

export function PhaseStepper({ phase, songTitle }: { phase: string; songTitle?: string | null }) {
  const order = ["A", "B", "C", "D", "E", "done"];
  const currentIdx = order.indexOf(phase);
  return (
    <div className="border-b bg-white px-3 py-2">
      {songTitle && <div className="mb-1 text-xs text-slate-500 truncate">🎵 {songTitle}</div>}
      <div className="flex items-center gap-1">
        {PHASES.map((p, i) => {
          const done = currentIdx > i || phase === "done";
          const active = phase === p.key;
          return (
            <div key={p.key} className="flex items-center gap-1">
              <div
                className={`flex h-6 items-center gap-1 rounded-full px-2 text-xs ${
                  active ? "bg-indigo-600 text-white" : done ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400"
                }`}
              >
                <span className="font-bold">{done && !active ? "✓" : p.key}</span>
                <span className="hidden sm:inline">{p.label}</span>
              </div>
              {i < PHASES.length - 1 && <span className="text-slate-300">›</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
