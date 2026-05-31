import { ReactNode } from "react";
import { CoachAvatar } from "@/components/character/Coach";

/** ブランドのロゴマーク = ソラ先生のキャラクター */
export function LogoMark({ size = 40 }: { size?: number }) {
  return <CoachAvatar size={size} />;
}

export function BrandWordmark({ size = 40, sub = true }: { size?: number; sub?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <CoachAvatar size={size} />
      <div className="leading-tight">
        <div className="text-lg font-bold tracking-tight text-slate-900">ソラ先生</div>
        {sub && <div className="text-[11px] font-medium text-brand-600">AIボーカルトレーナー</div>}
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
