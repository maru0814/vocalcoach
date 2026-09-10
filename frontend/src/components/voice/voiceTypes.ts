// 声タイプの共通定義（id・短い表示名・タイプ別テーマ）。フロント各所の単一ソース。
// id はバックエンドの VOICE_TYPES と一致させる（crystal/moody に改名済み）。

// タイプ別テーマ（docs/72）。診断結果ページ全体の「ステージ照明」をタイプ色に差し替える。
// - Tailwind クラス系トークンは JIT 検出のため必ず完全リテラルで書く（動的組み立て禁止）
// - studio / stage は多段グラデのため inline style 用の CSS 文字列で持つ
export type VTypeTheme = {
  /** 結果カードのグラデ（bg-gradient-to-br と併用） */
  grad: string;
  /** ページ全景の明るい照明（.bg-studio のタイプ色版。style.background に渡す） */
  studio: string;
  /** 結果パネル・最終CTAの夜ステージ照明（.bg-stage のタイプ色版。style.background に渡す） */
  stage: string;
  /** 明背景上の見出し・キッカー（白地コントラスト AA 以上） */
  accentText: string;
  /** 明背景上のテキストリンク */
  accentLink: string;
  /** 主CTA（塗り・文字・3D影。Button の tone に渡せる形） */
  button: string;
  /** 白ボタン上のタイプ色文字（暗いステージ内のCTA用） */
  buttonGhostText: string;
  /** 記事のセクションアイコンチップの地色（IconChip の tone） */
  chipBg: string;
  /** 記事の「SECTION NN」ラベル */
  sectionLabel: string;
  /** 記事の箇条書きの点 */
  bullet: string;
  /** 記事の締めボックスの地色 */
  closingBg: string;
  /** 記事の目次チップの hover */
  tocHover: string;
};

export const VTYPE_THEME: Record<string, VTypeTheme> = {
  rock: {
    grad: "from-rose-500 to-orange-500",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(251,113,133,0.35), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(253,186,116,0.30), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(244,63,94,0.18), transparent 60%), linear-gradient(180deg, #fff8f6 0%, #fdeeea 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(251,146,60,0.30), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(244,63,94,0.22), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(255,228,230,0.10), transparent 55%), linear-gradient(175deg, #4c0d1c 0%, #38081b 55%, #200409 100%)",
    accentText: "text-rose-600",
    accentLink: "text-rose-600 decoration-rose-200 hover:text-rose-700",
    button: "bg-rose-600 text-white shadow-[0_4px_0_#9f1239] active:shadow-[0_1px_0_#9f1239]",
    buttonGhostText: "text-rose-600",
    chipBg: "bg-rose-500",
    sectionLabel: "text-rose-300",
    bullet: "bg-rose-400",
    closingBg: "bg-rose-50/70",
    tocHover: "hover:border-rose-300 hover:text-rose-700",
  },
  groovy: {
    grad: "from-amber-500 to-yellow-600",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(252,211,77,0.40), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(251,191,36,0.30), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(217,119,6,0.15), transparent 60%), linear-gradient(180deg, #fffbf2 0%, #fbf2dd 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(251,191,36,0.30), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(245,158,11,0.20), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(254,243,199,0.08), transparent 55%), linear-gradient(175deg, #451a03 0%, #331302 55%, #1c0a01 100%)",
    accentText: "text-amber-700",
    accentLink: "text-amber-700 decoration-amber-200 hover:text-amber-800",
    button: "bg-amber-400 text-amber-950 shadow-[0_4px_0_#92400e] active:shadow-[0_1px_0_#92400e]",
    buttonGhostText: "text-amber-700",
    chipBg: "bg-amber-600",
    sectionLabel: "text-amber-300",
    bullet: "bg-amber-400",
    closingBg: "bg-amber-50/70",
    tocHover: "hover:border-amber-300 hover:text-amber-700",
  },
  pop: {
    grad: "from-sky-400 to-cyan-500",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(125,211,252,0.40), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(103,232,249,0.30), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(56,189,248,0.18), transparent 60%), linear-gradient(180deg, #f6fbff 0%, #e9f5fd 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(56,189,248,0.32), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(34,211,238,0.22), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(224,242,254,0.08), transparent 55%), linear-gradient(175deg, #0c4a6e 0%, #083a58 55%, #04263c 100%)",
    accentText: "text-sky-700",
    accentLink: "text-sky-700 decoration-sky-200 hover:text-sky-800",
    button: "bg-sky-700 text-white shadow-[0_4px_0_#0c4a6e] active:shadow-[0_1px_0_#0c4a6e]",
    buttonGhostText: "text-sky-700",
    chipBg: "bg-sky-500",
    sectionLabel: "text-sky-300",
    bullet: "bg-sky-400",
    closingBg: "bg-sky-50/70",
    tocHover: "hover:border-sky-300 hover:text-sky-700",
  },
  mysterious: {
    grad: "from-violet-600 to-indigo-800",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(196,181,253,0.42), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(165,180,252,0.32), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(139,92,246,0.18), transparent 60%), linear-gradient(180deg, #faf8ff 0%, #efeafc 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(167,139,250,0.30), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(129,140,248,0.20), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(236,72,153,0.08), transparent 55%), linear-gradient(175deg, #2e1065 0%, #251058 55%, #160a38 100%)",
    accentText: "text-violet-700",
    accentLink: "text-violet-700 decoration-violet-200 hover:text-violet-800",
    button: "bg-violet-600 text-white shadow-[0_4px_0_#4c1d95] active:shadow-[0_1px_0_#4c1d95]",
    buttonGhostText: "text-violet-700",
    chipBg: "bg-violet-600",
    sectionLabel: "text-violet-300",
    bullet: "bg-violet-400",
    closingBg: "bg-violet-50/70",
    tocHover: "hover:border-violet-300 hover:text-violet-700",
  },
  crystal: {
    grad: "from-cyan-200 via-sky-400 to-indigo-500",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(165,243,252,0.45), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(147,197,253,0.35), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(129,140,248,0.20), transparent 60%), linear-gradient(180deg, #f7fbff 0%, #edf1fe 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(165,243,252,0.26), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(129,140,248,0.28), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(219,234,254,0.10), transparent 55%), linear-gradient(175deg, #2a3572 0%, #1e2556 55%, #111536 100%)",
    accentText: "text-blue-600",
    accentLink: "text-blue-600 decoration-blue-200 hover:text-blue-700",
    button: "bg-blue-600 text-white shadow-[0_4px_0_#1e3a8a] active:shadow-[0_1px_0_#1e3a8a]",
    buttonGhostText: "text-blue-600",
    chipBg: "bg-blue-500",
    sectionLabel: "text-blue-300",
    bullet: "bg-blue-400",
    closingBg: "bg-blue-50/70",
    tocHover: "hover:border-blue-300 hover:text-blue-700",
  },
  dramatic: {
    grad: "from-fuchsia-500 to-purple-700",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(240,171,252,0.38), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(232,121,249,0.25), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(192,38,211,0.14), transparent 60%), linear-gradient(180deg, #fef7ff 0%, #faeafe 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(232,121,249,0.30), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(217,70,239,0.20), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(253,224,71,0.06), transparent 55%), linear-gradient(175deg, #4a044e 0%, #3b0764 55%, #22043a 100%)",
    accentText: "text-fuchsia-700",
    accentLink: "text-fuchsia-700 decoration-fuchsia-200 hover:text-fuchsia-800",
    button: "bg-fuchsia-700 text-white shadow-[0_4px_0_#701a75] active:shadow-[0_1px_0_#701a75]",
    buttonGhostText: "text-fuchsia-700",
    chipBg: "bg-fuchsia-600",
    sectionLabel: "text-fuchsia-300",
    bullet: "bg-fuchsia-400",
    closingBg: "bg-fuchsia-50/70",
    tocHover: "hover:border-fuchsia-300 hover:text-fuchsia-700",
  },
  whisper: {
    grad: "from-emerald-400 to-teal-500",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(110,231,183,0.35), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(94,234,212,0.28), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(52,211,153,0.16), transparent 60%), linear-gradient(180deg, #f4fdf9 0%, #e7f9f1 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(52,211,153,0.28), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(45,212,191,0.20), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(209,250,229,0.07), transparent 55%), linear-gradient(175deg, #064e3b 0%, #043f33 55%, #022018 100%)",
    accentText: "text-emerald-700",
    accentLink: "text-emerald-700 decoration-emerald-200 hover:text-emerald-800",
    button: "bg-emerald-700 text-white shadow-[0_4px_0_#064e3b] active:shadow-[0_1px_0_#064e3b]",
    buttonGhostText: "text-emerald-700",
    chipBg: "bg-emerald-500",
    sectionLabel: "text-emerald-300",
    bullet: "bg-emerald-400",
    closingBg: "bg-emerald-50/70",
    tocHover: "hover:border-emerald-300 hover:text-emerald-700",
  },
  moody: {
    grad: "from-slate-500 to-cyan-950",
    studio:
      "radial-gradient(1200px 600px at 10% -10%, rgba(148,163,184,0.35), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(103,232,249,0.14), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(71,85,105,0.20), transparent 60%), linear-gradient(180deg, #f6f8fb 0%, #e8edf3 100%)",
    stage:
      "radial-gradient(600px 400px at 50% -10%, rgba(148,163,184,0.25), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(34,211,238,0.10), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(226,232,240,0.06), transparent 55%), linear-gradient(175deg, #1e293b 0%, #16202f 55%, #0b1120 100%)",
    accentText: "text-slate-700",
    accentLink: "text-slate-700 decoration-slate-300 hover:text-slate-900",
    button: "bg-slate-700 text-white shadow-[0_4px_0_#0f172a] active:shadow-[0_1px_0_#0f172a]",
    buttonGhostText: "text-slate-700",
    chipBg: "bg-slate-600",
    sectionLabel: "text-slate-400",
    bullet: "bg-slate-400",
    closingBg: "bg-slate-100/70",
    tocHover: "hover:border-slate-400 hover:text-slate-800",
  },
};

// 未知の typeId 用フォールバック（brand 相当＝従来配色。globals.css の .bg-studio / .bg-stage と同値）
export const VTYPE_FALLBACK_THEME: VTypeTheme = {
  grad: "from-brand-500 to-pink-500",
  studio:
    "radial-gradient(1200px 600px at 10% -10%, rgba(167,139,250,0.38), transparent 60%), radial-gradient(1000px 500px at 100% 0%, rgba(244,114,182,0.28), transparent 55%), radial-gradient(900px 700px at 50% 120%, rgba(99,102,241,0.25), transparent 60%), linear-gradient(180deg, #faf9ff 0%, #f1eefb 100%)",
  stage:
    "radial-gradient(600px 400px at 50% -10%, rgba(251,191,36,0.14), transparent 60%), radial-gradient(800px 500px at 85% 20%, rgba(34,211,238,0.10), transparent 55%), radial-gradient(700px 500px at 10% 80%, rgba(236,72,153,0.12), transparent 55%), linear-gradient(175deg, #1e1655 0%, #171045 55%, #0f0a2e 100%)",
  accentText: "text-brand-600",
  accentLink: "text-brand-600 decoration-brand-200 hover:text-brand-700",
  button: "bg-brand-600 text-white shadow-[0_4px_0_#5b21b6] active:shadow-[0_1px_0_#5b21b6]",
  buttonGhostText: "text-brand-700",
  chipBg: "bg-brand-600",
  sectionLabel: "text-brand-300",
  bullet: "bg-brand-400",
  closingBg: "bg-brand-50/70",
  tocHover: "hover:border-brand-300 hover:text-brand-700",
};

export function vtypeTheme(id: string | null | undefined): VTypeTheme {
  return (id && VTYPE_THEME[id]) || VTYPE_FALLBACK_THEME;
}

// 後方互換: 結果カード等が参照するグラデは VTYPE_THEME.grad から導出（二重定義しない）
export const VTYPE_STYLE: Record<string, string> = Object.fromEntries(
  Object.entries(VTYPE_THEME).map(([id, t]) => [id, t.grad]),
);

export type VoiceTypeListItem = { id: string; name: string };

// ギャラリー表示順（短い英語名）
export const VOICE_TYPE_LIST: VoiceTypeListItem[] = [
  { id: "rock", name: "Rock" },
  { id: "groovy", name: "Groovy" },
  { id: "pop", name: "Pop" },
  { id: "mysterious", name: "Mysterious" },
  { id: "crystal", name: "Crystal" },
  { id: "dramatic", name: "Dramatic" },
  { id: "whisper", name: "Whisper" },
  { id: "moody", name: "Moody" },
];

// 共有ランディング/OGP用のタイプ別メタ（backend VOICE_TYPES と一致）
export type VoiceTypeMeta = { name: string; emoji: string; desc: string };
export const VOICE_TYPE_META: Record<string, VoiceTypeMeta> = {
  rock: { name: "Rock Voice", emoji: "🔥", desc: "芯のある地声成分で、明るくまっすぐ前に出るパワフルな声。" },
  groovy: { name: "Groovy Voice", emoji: "🎙", desc: "太く温かい地声成分。うねるような厚みとコクのある声。" },
  pop: { name: "Pop Voice", emoji: "🌤", desc: "自然体で親しみやすい、軽やかで明るい地声成分の声。" },
  mysterious: { name: "Mysterious Voice", emoji: "🌒", desc: "翳りのある深い地声成分。浮遊感と余韻をまとう声。" },
  crystal: { name: "Crystal Voice", emoji: "💎", desc: "高く抜ける裏声成分に芯がある、きらびやかな声。" },
  dramatic: { name: "Dramatic Voice", emoji: "🎭", desc: "裏声成分に情感と伸びがある、切なく響くドラマチックな声。" },
  whisper: { name: "Whisper Voice", emoji: "🍃", desc: "やわらかく透明な裏声成分。そっと寄り添う軽やかな声。" },
  moody: { name: "Moody Voice", emoji: "🌙", desc: "息まじりの深い裏声成分。しっとり包み込む大人の声。" },
};

// 絶対URL生成のベース（OG画像は絶対URL必須）。本番は同一ドメイン配信なので API ベース＝サイト origin。
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:3000"
).replace(/\/$/, "");
