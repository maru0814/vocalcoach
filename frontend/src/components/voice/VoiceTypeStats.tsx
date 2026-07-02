"use client";

import { useEffect, useState } from "react";
import { getVoiceTypeStats, VoiceTypeStats as Stats } from "@/lib/api";

// 社会的証明：累計診断数＋いま人気のタイプ。新規の見栄え対策で件数が少ないうちは非表示。
const MIN_SHOW = 15;

export function VoiceTypeStats({
  className = "",
  tone = "light",
}: {
  className?: string;
  tone?: "light" | "dark"; // dark = 暗面（bg-stage）上での表示用
}) {
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => {
    getVoiceTypeStats().then(setS).catch(() => {});
  }, []);
  if (!s || s.total < MIN_SHOW) return null;
  const base = tone === "dark" ? "text-white/60" : "text-slate-500";
  const strong = tone === "dark" ? "text-white" : "text-slate-700";
  const accent = tone === "dark" ? "text-brand-200" : "text-brand-600";
  return (
    <div className={`text-center text-xs ${base} ${className}`}>
      🎤 これまで <b className={strong}>{s.total.toLocaleString()}</b> 人が診断
      {s.top ? (
        <> ・いま人気は <b className={accent}>{s.top.name}</b></>
      ) : null}
    </div>
  );
}
