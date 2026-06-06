"use client";

import { VoiceTypeArt } from "./VoiceTypeArt";
import { VTYPE_STYLE } from "./voiceTypes";

// 声タイプ診断の結果表示（独立機能・チャット双方で再利用）。
// スクショ映え＆Xシェアを通じたゼロ円集客の入口。
export { VTYPE_STYLE };

/** 声タイプ診断（シェアの目玉）。モチーフ画像のバナー＋スコア。スクショ映えする1枚に。 */
export function VoiceTypeBlock({ vt, score, shareRef }: { vt: any; score: number; shareRef?: any }) {
  if (!vt) return null;
  const grad = VTYPE_STYLE[vt.id] || "from-brand-500 to-pink-500";
  const ax = vt.axes_jp || {};
  const near = vt.near || {};
  const tag = (k: string, v: string) => (near[k] ? "やや" : "") + v;
  return (
    <div ref={shareRef} className={`overflow-hidden rounded-2xl bg-gradient-to-br ${grad} text-white shadow-soft`}>
      {/* モチーフ画像バナー（未用意のタイプはマスコットに自動フォールバック） */}
      <div className="relative aspect-[16/9] w-full">
        <VoiceTypeArt id={vt.id} fallbackMascotSize={88} className="h-full w-full" />
        <div className="absolute left-3 top-3 rounded-full bg-black/35 px-2 py-0.5 text-[11px] font-bold tracking-wide backdrop-blur-sm">
          🎤 ソラ先生 声タイプ診断
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2">
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
