import { ReactNode } from "react";

/** マイクのSVGロゴマーク（グラデーション円の中に配置） */
export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-2xl bg-brand-gradient shadow-soft"
      style={{ width: size, height: size }}
    >
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24" fill="none" aria-hidden>
        <rect x="9" y="2" width="6" height="12" rx="3" fill="white" />
        <path
          d="M5 11a7 7 0 0 0 14 0M12 18v3M8.5 21h7"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

export function BrandWordmark({ size = 40, sub = true }: { size?: number; sub?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark size={size} />
      <div className="leading-tight">
        <div className="text-lg font-bold tracking-tight text-slate-900">こえのアトリエ</div>
        {sub && <div className="text-[11px] font-medium text-brand-600">AI VOCAL TRAINER</div>}
      </div>
    </div>
  );
}

export function Pill({ children, tone = "brand" }: { children: ReactNode; tone?: "brand" | "rose" | "emerald" | "amber" | "slate" }) {
  const tones: Record<string, string> = {
    brand: "bg-brand-50 text-brand-700",
    rose: "bg-rose-50 text-rose-600",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
