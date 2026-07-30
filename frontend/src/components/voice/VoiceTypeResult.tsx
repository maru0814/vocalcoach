"use client";

import { VoiceTypeArt } from "./VoiceTypeArt";
import { Icon } from "@/components/site/IconChip";
import { VTYPE_STYLE } from "./voiceTypes";
import { VoiceAxisBars, posFromAxes } from "./VoiceAxisBars";

// 声タイプ診断の結果表示（独立機能・チャット双方で再利用）。
// スクショ映え＆Xシェアを通じたゼロ円集客の入口。
export { VTYPE_STYLE };

/** 声タイプ診断（シェアの目玉）。モチーフ画像のバナー＋スコア。スクショ映えする1枚に。
 *  maskArtists=true は近い歌手名を伏せ字にして登録誘導（LPのティザー用。実名はDOMに出さない）。 */
export function VoiceTypeBlock({
  vt,
  score,
  shareRef,
  maskArtists = false,
}: {
  vt: any;
  score: number;
  shareRef?: any;
  maskArtists?: boolean;
}) {
  if (!vt) return null;
  const grad = VTYPE_STYLE[vt.id] || "from-brand-500 to-pink-500";
  // 3軸バーの位置。旧応答（axes_pos なし）は二値＋境界フラグから復元する（docs/83）
  const axisPos = vt.axes_pos || posFromAxes(vt.axes, vt.near);
  return (
    <div ref={shareRef} className={`overflow-hidden rounded-2xl bg-gradient-to-br ${grad} text-white shadow-soft`}>
      {/* モチーフ画像バナー（未用意のタイプはマスコットに自動フォールバック） */}
      <div className="relative aspect-[16/9] w-full">
        <VoiceTypeArt id={vt.id} fallbackMascotSize={88} className="h-full w-full" />
        <div className="absolute left-3 top-3 rounded-full bg-black/35 px-2 py-0.5 text-[11px] font-bold tracking-wide backdrop-blur-sm">
          <Icon name="mic" size={11} className="mr-1 inline-block align-[-1px]" />ソラ先生 声タイプ診断
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black leading-none">{vt.name}</span>
          <span className="ml-auto text-right text-xs text-white/80">総合<br /><b className="text-lg">{score}</b></span>
        </div>
        <p className="mt-1.5 text-[13px] font-medium leading-snug text-white/95">{vt.desc}</p>
        <VoiceAxisBars pos={axisPos} tone="onColor" className="mt-3" />
        {vt.artists && (vt.artists.female || vt.artists.male) && !maskArtists && (
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
        {maskArtists && (
          <div className="mt-2 rounded-xl bg-black/20 px-3 py-2 text-[11px]">
            <div className="text-white/70">声質が近い歌手</div>
            <div className="mt-1 flex items-center gap-2">
              <span aria-hidden className="font-bold tracking-widest text-white/50">●●●● ・ ●●●●</span>
              <span className="ml-auto whitespace-nowrap rounded-full bg-white px-2.5 py-0.5 text-[11px] font-bold text-brand-700">
                🔒 無料登録でひらく
              </span>
            </div>
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
  // タイプ別の共有ランディング（Xでカード画像＝OGPが出る）。スコアを ?s= で渡しOGタイトルに反映。
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const shareUrl = `${origin}/voice-type/share/${vt.id}?s=${score}`;
  const near = [vt.artists?.female?.[0], vt.artists?.male?.[0]].filter(Boolean).join("・");
  const text =
    `🎤 わたしの声タイプは【${vt.name}${vt.emoji}】総合${score}点でした！\n` +
    (near ? `声質が近い例：${near}\n` : "") +
    `あなたは何タイプ？15秒で診断して、結果を見せ合おう👇\n#声診断 #ボイトレ #ソラ先生`;
  const xUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`;
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
    <div className="space-y-1.5">
      <p className="px-1 text-center text-[11px] font-bold text-slate-500">
        友達と結果を見せ合うと盛り上がります。シェアして「君は何タイプ？」
      </p>
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
          <Icon name="image" size={15} /> 画像で保存
        </button>
      </div>
    </div>
  );
}
