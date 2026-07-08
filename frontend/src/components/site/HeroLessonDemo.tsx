"use client";

import { useEffect, useRef, useState } from "react";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";

/**
 * ヒーロー用・自動再生のレッスンデモ（LPのFB反映）。
 * 「録音＋言葉で送る → 原因指摘＋基礎練 → やってみる → 録り直し → 褒められる」
 * の Before→After をループで動的に見せる。曲名は例示（Mrs. GREEN APPLE『ライラック』）。
 */

const WAVE = [8, 14, 10, 16, 9, 13, 7];

function RecordingBubble({ label }: { label: string }) {
  return (
    <div className="ml-auto flex w-fit max-w-[85%] items-center gap-2 rounded-2xl rounded-br-md bg-brand-600 px-3 py-2">
      <span className="flex items-end gap-0.5" aria-hidden>
        {WAVE.map((h, i) => (
          <span key={i} className="w-[3px] rounded-full bg-white/80" style={{ height: h }} />
        ))}
      </span>
      <span className="text-xs font-bold text-white">{label}</span>
    </div>
  );
}

function UserBubble({ children }: { children: string }) {
  return (
    <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-md bg-brand-600 px-3 py-2 text-xs leading-relaxed text-white">
      {children}
    </p>
  );
}

function SoraBubble({ children }: { children: string }) {
  return (
    <div className="flex items-end gap-1.5">
      <CoachAvatar size={20} />
      <p className="max-w-[85%] rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2 text-xs leading-relaxed text-slate-700">
        {children}
      </p>
    </div>
  );
}

function Typing() {
  return (
    <div className="flex items-end gap-1.5">
      <CoachAvatar size={20} />
      <span className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-slate-400"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </span>
    </div>
  );
}

// step境界（ms）。合計 ~17.5s でループ
const SCRIPT: Array<{ at: number; key: string }> = [
  { at: 300, key: "u-text" },
  { at: 1300, key: "u-rec1" },
  { at: 2300, key: "typing1" },
  { at: 3800, key: "s-cause" },
  { at: 6600, key: "s-menu" },
  { at: 9400, key: "u-done" },
  { at: 10600, key: "u-rec2" },
  { at: 11600, key: "typing2" },
  { at: 13100, key: "s-praise" },
];
const TOTAL = 17500;

export function HeroLessonDemo() {
  const [elapsed, setElapsed] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const run = () => {
      setElapsed(0);
      timers.current.forEach(clearTimeout);
      timers.current = SCRIPT.map((s) => setTimeout(() => setElapsed(s.at), s.at));
    };
    run();
    const loop = setInterval(run, TOTAL);
    return () => {
      timers.current.forEach(clearTimeout);
      clearInterval(loop);
    };
  }, []);

  const on = (key: string) => {
    const step = SCRIPT.find((s) => s.key === key);
    return step ? elapsed >= step.at : false;
  };
  // typingは次の吹き出しが出たら消す
  const typing1 = on("typing1") && !on("s-cause");
  const typing2 = on("typing2") && !on("s-praise");

  return (
    <div className="rounded-2xl bg-white p-3 shadow-card">
      <div className="flex items-center gap-2 border-b border-slate-100 px-1 pb-2">
        <CoachAvatar size={24} />
        <span className="text-xs font-bold text-slate-700">{COACH_NAME}</span>
        <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
          オンライン
        </span>
      </div>
      <div className="flex h-[340px] flex-col justify-end gap-2 overflow-hidden px-1 pb-1 pt-3">
        {on("u-text") && (
          <div className="animate-pop-in">
            <UserBubble>Mrs. GREEN APPLEの『ライラック』のサビを歌ってみたけど、高音で裏返っちゃいます…</UserBubble>
          </div>
        )}
        {on("u-rec1") && (
          <div className="animate-pop-in">
            <RecordingBubble label="録音を送信（0:28）" />
          </div>
        )}
        {typing1 && <Typing />}
        {on("s-cause") && (
          <div className="animate-pop-in">
            <SoraBubble>
              2:10、地声のまま押し上げて裏返りかけていますね。息の支えを作って、ミックスボイスに切り替えましょう
            </SoraBubble>
          </div>
        )}
        {on("s-menu") && (
          <div className="animate-pop-in">
            <SoraBubble>今日の基礎練は2つ。①ドッグブレス30秒×3 ②“ネイネイ”で高音に軽く当てる、です🎵</SoraBubble>
          </div>
        )}
        {on("u-done") && (
          <div className="animate-pop-in">
            <UserBubble>基礎練やってみました！もう一回歌います</UserBubble>
          </div>
        )}
        {on("u-rec2") && (
          <div className="animate-pop-in">
            <RecordingBubble label="録音を送信（0:26）" />
          </div>
        )}
        {typing2 && <Typing />}
        {on("s-praise") && (
          <div className="animate-pop-in">
            <SoraBubble>裏返らずに当たりましたね！ミックスの入り口に立てています。この調子です👏</SoraBubble>
          </div>
        )}
      </div>
    </div>
  );
}
