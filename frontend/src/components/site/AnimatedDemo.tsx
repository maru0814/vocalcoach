"use client";

import { useEffect, useRef, useState } from "react";
import { CoachAvatar, COACH_NAME } from "@/components/character/Coach";
import { Icon } from "@/components/site/IconChip";

/**
 * 「使っている様子」を自動再生するデモ。
 * 録音 → 送信 → 解析中 → 会話で感想 → 練習提案、をループ（採点カード・点数は出さない）。
 */
export function AnimatedDemo() {
  // step: 0=録音中, 1=ユーザー送信, 2=解析中(typing), 3=感想チャット, 4=練習提案
  const [step, setStep] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const TOTAL = 11000;

    const run = () => {
      setStep(0);
      timers.current.push(setTimeout(() => setStep(1), 1800));
      timers.current.push(setTimeout(() => setStep(2), 3000));
      timers.current.push(setTimeout(() => setStep(3), 4600));
      timers.current.push(setTimeout(() => setStep(4), 7200));
    };

    run();
    const loop = setInterval(run, TOTAL);
    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
      clearInterval(loop);
    };
  }, []);

  return (
    <div className="mx-auto w-full max-w-[320px]">
      <div className="relative">
        {/* フローティングバッジ（フレームに対して相対配置） */}
        <div className="absolute -right-3 -top-3 z-10 flex animate-floaty items-center gap-1 rounded-2xl bg-white px-3 py-2 text-xs font-bold text-brand-600 shadow-soft">
          <Icon name="mic" size={12} /> 録音するだけ
        </div>
        <div className="absolute -bottom-3 -left-3 z-10 flex items-center gap-1 rounded-2xl bg-white px-3 py-2 text-xs font-bold text-brand-600 shadow-soft">
          <Icon name="sparkles" size={12} /> その場で添削
        </div>

        {/* 端末フレーム */}
        <div className="rounded-[2rem] border-4 border-white/70 bg-white/95 p-3 shadow-2xl">
        {/* ヘッダー */}
        <div className="mb-2 flex items-center gap-2 border-b border-slate-100 pb-2">
          <CoachAvatar size={28} />
          <div className="leading-none">
            <div className="text-xs font-bold text-slate-700">{COACH_NAME}</div>
            <div className="text-[9px] text-brand-600">AIボーカルトレーナー・オンライン</div>
          </div>
        </div>

        {/* 会話エリア（高さ固定でガタつき防止） */}
        <div className="flex h-[320px] flex-col justify-end gap-2 overflow-hidden">
          {/* 録音中インジケーター */}
          {step === 0 && (
            <div key="rec" className="mx-auto flex animate-pop-in flex-col items-center gap-2 py-8">
              <div className="flex items-center gap-2 rounded-full bg-rose-50 px-4 py-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-rose-400" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
                </span>
                <span className="text-xs font-bold text-rose-600">録音中…</span>
              </div>
              <div className="flex h-8 items-center gap-1">
                {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
                  <span
                    key={i}
                    className="block w-1.5 origin-center animate-eq rounded-full bg-brand-400"
                    style={{ height: 22, animationDelay: `${i * 0.09}s` }}
                  />
                ))}
              </div>
              <div className="text-[10px] text-slate-400">サビの高音を歌っています…</div>
            </div>
          )}

          {/* ユーザー送信 */}
          {step >= 1 && (
            <div key="user" className="flex animate-pop-in justify-end">
              <div className="flex items-center gap-2 rounded-2xl rounded-br-md bg-brand-600 px-3 py-2 text-[11px] text-white">
                <span className="flex items-center gap-0.5">
                  {[6, 12, 8, 14, 9].map((h, i) => (
                    <span key={i} className="block w-1 rounded-full bg-white/80" style={{ height: h }} />
                  ))}
                </span>
                録音を送信（0:25）
              </div>
            </div>
          )}

          {/* 解析中 typing */}
          {step === 2 && (
            <div key="typing" className="flex animate-pop-in items-center gap-2">
              <CoachAvatar size={28} />
              <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-slate-100 px-3 py-2.5">
                <span className="text-[10px] text-slate-400">解析しています</span>
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" />
                  <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.2s" }} />
                  <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.4s" }} />
                </span>
              </div>
            </div>
          )}

          {/* 感想・気づき（会話文。採点カード・点数は出さない） */}
          {step >= 3 && (
            <div key="fb" className="flex animate-pop-in items-end gap-2">
              <CoachAvatar size={28} />
              <div className="flex-1 rounded-2xl rounded-bl-md bg-white px-3 py-2.5 text-[11px] font-medium leading-relaxed text-slate-700 shadow ring-1 ring-slate-100">
                サビの高音、地声で押していて裏返りそうですね。喉が少し詰まって聞こえます。ミックスボイスで軽く前に当てると、楽に届きますよ🎤
              </div>
            </div>
          )}

          {/* 基礎練の提案（具体的な3ステップ指導） */}
          {step >= 4 && (
            <div key="practice" className="flex animate-pop-in items-end gap-2">
              <CoachAvatar size={28} />
              <div className="rounded-2xl rounded-bl-md bg-brand-50 px-3 py-2 text-[11px] leading-relaxed text-slate-700">
                コツは3ステップ😊<br />
                <span className="font-bold text-brand-700">① ハミング</span>で鼻に響かせる →{" "}
                <span className="font-bold text-brand-700">②「ネイネイ」</span>で細く高音へ →{" "}
                <span className="font-bold text-brand-700">③「ナンナン」</span>で厚みを足す。<br />
                換声点がスッとつながりますよ🎬
              </div>
            </div>
          )}
        </div>
        </div>
      </div>

      <p className="mt-8 text-center text-xs text-slate-400">▲ 実際のレッスンの流れ（自動再生）</p>
    </div>
  );
}
