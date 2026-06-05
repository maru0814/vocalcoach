"use client";

import { VoiceTypeMascot } from "./VoiceTypeMascot";

// 声タイプ診断の結果表示（独立機能・チャット双方で再利用）。
// スクショ映え＆Xシェアを通じたゼロ円集客の入口。

export const VTYPE_STYLE: Record<string, string> = {
  rock: "from-rose-500 to-orange-500", groovy: "from-amber-500 to-yellow-600",
  pop: "from-sky-400 to-cyan-500", mysterious: "from-violet-600 to-indigo-700",
  husky: "from-cyan-400 to-blue-500", dramatic: "from-fuchsia-600 to-purple-700",
  whisper: "from-emerald-400 to-teal-500", sexy: "from-slate-600 to-indigo-900",
};

/** 声タイプ診断（シェアの目玉）。スクショ映えする1枚に。 */
export function VoiceTypeBlock({ vt, score, shareRef }: { vt: any; score: number; shareRef?: any }) {
  if (!vt) return null;
  const grad = VTYPE_STYLE[vt.id] || "from-brand-500 to-pink-500";
  const ax = vt.axes_jp || {};
  const near = vt.near || {};
  const tag = (k: string, v: string) => (near[k] ? "やや" : "") + v;
  return (
    <div ref={shareRef} className={`overflow-hidden rounded-2xl bg-gradient-to-br ${grad} p-4 text-white shadow-soft`}>
      <div className="text-[11px] font-bold tracking-wide text-white/80">🎤 ソラ先生 声タイプ診断</div>
      <div className="mt-1 flex items-center gap-2">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/25 shadow-inner">
          <VoiceTypeMascot id={vt.id} size={42} />
        </span>
        <span className="text-2xl font-black leading-none">{vt.name}</span>
        <span className="ml-auto text-right text-xs text-white/80">総合<br /><b className="text-lg">{score}</b></span>
      </div>
      <p className="mt-1.5 text-[13px] font-medium leading-snug text-white/95">{vt.desc}</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {[tag("register", ax.register), tag("power", ax.power), tag("color", ax.color)].filter(Boolean).map((t: string, i: number) => (
          <span key={i} className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-bold">{t}</span>
        ))}
      </div>
      {vt.artists && (vt.artists.female || vt.artists.male) && (
        <div className="mt-2 space-y-0.5 text-[11px] text-white/95">
          <div className="text-white/70">声質が近い例</div>
          {Array.isArray(vt.artists.female) && vt.artists.female.length > 0 && (
            <div>♀ {vt.artists.female.join("・")}</div>
          )}
          {Array.isArray(vt.artists.male) && vt.artists.male.length > 0 && (
            <div>♂ {vt.artists.male.join("・")}</div>
          )}
        </div>
      )}
      <div className="mt-2 text-[9px] text-white/60">※ 声の傾向からの推定です（優劣ではありません）</div>
    </div>
  );
}

/** Xシェア＋画像保存。診断結果を拡散の入口にする。 */
export function ShareButtons({ vt, score, shareRef }: { vt: any; score: number; shareRef: any }) {
  if (!vt) return null;
  const appUrl = typeof window !== "undefined" ? window.location.origin : "";
  const near = [vt.artists?.female?.[0], vt.artists?.male?.[0]].filter(Boolean).join("・");
  const text =
    `🎤 ソラ先生の発声診断、わたしの声タイプは【${vt.name}${vt.emoji}】でした！\n` +
    (near ? `声質が近い例：${near}\n` : "") +
    `あなたの声も無料で診断👉\n#声診断 #ボイトレ #ソラ先生`;
  const xUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(appUrl)}`;
  async function saveImage() {
    try {
      const mod = await import("html2canvas");
      const el = shareRef.current;
      if (!el) return;
      const canvas = await mod.default(el, { scale: 2, backgroundColor: null });
      const a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = `soramirai-voicetype-${vt.id}.png`;
      a.click();
    } catch {
      /* html2canvas 失敗時は何もしない（Xシェアは使える） */
    }
  }
  return (
    <div className="flex gap-2">
      <a
        href={xUrl} target="_blank" rel="noreferrer"
        className="flex flex-1 items-center justify-center gap-1.5 rounded-full bg-slate-900 px-3 py-2 text-sm font-bold text-white transition active:scale-95"
      >
        𝕏 で結果をシェア
      </a>
      <button
        type="button" onClick={saveImage}
        className="flex items-center justify-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 transition active:scale-95"
      >
        🖼 画像で保存
      </button>
    </div>
  );
}
