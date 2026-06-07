"use client";

import { useEffect, useState } from "react";
import { getVoiceTypeStats, VoiceTypeStats as Stats } from "@/lib/api";

// 社会的証明：累計診断数＋いま人気のタイプ。新規の見栄え対策で件数が少ないうちは非表示。
const MIN_SHOW = 15;

export function VoiceTypeStats({ className = "" }: { className?: string }) {
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => {
    getVoiceTypeStats().then(setS).catch(() => {});
  }, []);
  if (!s || s.total < MIN_SHOW) return null;
  return (
    <div className={`text-center text-xs text-slate-500 ${className}`}>
      🎤 これまで <b className="text-slate-700">{s.total.toLocaleString()}</b> 人が診断
      {s.top ? (
        <> ・いま人気は <b className="text-brand-600">{s.top.name}</b></>
      ) : null}
    </div>
  );
}
