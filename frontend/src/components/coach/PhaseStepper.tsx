"use client";

const PHASES: { key: string; label: string; icon: string }[] = [
  { key: "A", label: "曲指定", icon: "🎵" },
  { key: "B", label: "課題発見", icon: "🔍" },
  { key: "C", label: "基礎練", icon: "🎯" },
  { key: "D", label: "練習確認", icon: "✅" },
  { key: "E", label: "再録音", icon: "📈" },
];

export function PhaseStepper({ phase, songTitle }: { phase: string; songTitle?: string | null }) {
  const order = ["A", "B", "C", "D", "E", "done"];
  const currentIdx = order.indexOf(phase);

  return (
    <div className="glass border-b border-white/40 px-3 pb-2.5 pt-2 shadow-sm">
      {songTitle && (
        <div className="mb-2 flex items-center gap-1.5 truncate px-1 text-xs text-slate-500">
          <span>🎵</span>
          <span className="truncate">{songTitle}</span>
        </div>
      )}
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
