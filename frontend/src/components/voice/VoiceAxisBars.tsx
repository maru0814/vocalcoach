// 声タイプ3軸バー（正本: docs/83）。
// 診断結果カード（測定位置）とタイプ別記事ページ（タイプ固定位置）で同じ部品を使い、
// 「自分の位置」と「タイプの位置」を同じ物差しで見比べられるようにする。
// 位置は 0=左ラベルの極 / 0.5=どちらとも言えない / 1=右ラベルの極。
// 中央基準の偏差バーにしているのは、「地声成分が何%」という量の誤読を防ぐため（測っているのは偏り）。

export type VoiceAxisPos = { register?: number; power?: number; color?: number };

type AxisKey = keyof VoiceAxisPos;

const AXES: { key: AxisKey; left: string; right: string }[] = [
  { key: "register", left: "地声寄り", right: "裏声寄り" },
  { key: "power", left: "パワフル", right: "ソフト" },
  { key: "color", left: "明るめ", right: "暗め" },
];

// docs/83 §4: マーカーが端で切れないよう描画位置を内側に丸める
const draw = (p: number) => Math.max(0.06, Math.min(0.94, p));
// |s|<0.4 が「境界に近い」＝ pos では中央±0.133（0.4/3）
const isNear = (p: number) => Math.abs(p - 0.5) < 0.4 / 3;

/** タイプ別記事ページ用の固定位置（8タイプ＝3軸の全組み合わせ。docs/83 §2） */
export const VTYPE_AXES: Record<string, Required<VoiceAxisPos>> = {
  rock: { register: 0.18, power: 0.18, color: 0.18 },
  groovy: { register: 0.18, power: 0.18, color: 0.82 },
  pop: { register: 0.18, power: 0.82, color: 0.18 },
  mysterious: { register: 0.18, power: 0.82, color: 0.82 },
  crystal: { register: 0.82, power: 0.18, color: 0.18 },
  dramatic: { register: 0.82, power: 0.18, color: 0.82 },
  whisper: { register: 0.82, power: 0.82, color: 0.18 },
  moody: { register: 0.82, power: 0.82, color: 0.82 },
};

/** axes_pos が無い応答（旧バックエンド・キャッシュ済み結果）用に二値＋境界フラグから位置を復元する */
export function posFromAxes(
  axes: { register?: string; power?: string; color?: string } | null | undefined,
  near?: { register?: boolean; power?: boolean; color?: boolean } | null,
): VoiceAxisPos | null {
  if (!axes) return null;
  const LEFT: Record<string, true> = { chest: true, power: true, clear: true };
  const out: VoiceAxisPos = {};
  for (const { key } of AXES) {
    const v = axes[key];
    if (!v) continue;
    const offset = near?.[key] ? 0.15 : 0.32;
    out[key] = LEFT[v] ? 0.5 - offset : 0.5 + offset;
  }
  return Object.keys(out).length ? out : null;
}

const TONE = {
  surface: {
    label: "text-[11px] font-bold text-slate-500",
    track: "bg-slate-200",
    tick: "bg-slate-300",
    fill: "bg-brand-500",
    marker: "bg-brand-600 ring-2 ring-white",
    caption: "text-[10px] text-slate-400",
  },
  onColor: {
    label: "text-[10px] font-bold text-white/90",
    track: "bg-white/25",
    tick: "bg-white/40",
    fill: "bg-white/70",
    marker: "bg-white ring-2 ring-white/50",
    caption: "text-[9px] text-white/60",
  },
} as const;

export function VoiceAxisBars({
  pos,
  tone = "surface",
  caption,
  className = "",
}: {
  pos: VoiceAxisPos | null | undefined;
  tone?: keyof typeof TONE;
  caption?: string;
  className?: string;
}) {
  if (!pos) return null;
  const rows = AXES.map((a) => ({ ...a, p: pos[a.key] })).filter(
    (r): r is typeof r & { p: number } => typeof r.p === "number",
  );
  if (rows.length === 0) return null;

  const t = TONE[tone];
  return (
    <div className={className}>
      <div className="flex flex-col gap-3">
        {rows.map(({ key, left, right, p }) => {
          const d = draw(p);
          const near = isNear(p);
          const side = p <= 0.5 ? left : right;
          return (
            <div key={key} className="flex items-center gap-2">
              <span className={`w-[4.5em] shrink-0 text-right ${t.label}`}>{left}</span>
              <div
                role="img"
                aria-label={`${left}から${right}のうち、${near ? "やや" : ""}${side}`}
                className="relative h-3 flex-1"
              >
                <div
                  aria-hidden
                  className={`absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full ${t.track}`}
                />
                <div
                  aria-hidden
                  className={`absolute left-1/2 top-1/2 h-3 w-px -translate-x-1/2 -translate-y-1/2 ${t.tick}`}
                />
                <div
                  aria-hidden
                  className={`absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full ${t.fill}`}
                  style={{
                    left: `${Math.min(50, d * 100)}%`,
                    width: `${Math.abs(d * 100 - 50)}%`,
                  }}
                />
                <div
                  aria-hidden
                  className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ${t.marker}`}
                  style={{ left: `${d * 100}%` }}
                />
              </div>
              <span className={`w-[4.5em] shrink-0 ${t.label}`}>{right}</span>
            </div>
          );
        })}
      </div>
      {caption && <p className={`mt-2 ${t.caption}`}>{caption}</p>}
    </div>
  );
}
