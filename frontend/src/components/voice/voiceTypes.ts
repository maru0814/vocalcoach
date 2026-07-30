// 声タイプの共通定義（id・短い表示名・グラデ）。フロント各所の単一ソース。
// id はバックエンドの VOICE_TYPES と一致させる（crystal/moody に改名済み）。

export const VTYPE_STYLE: Record<string, string> = {
  rock: "from-rose-500 to-orange-500",
  groovy: "from-amber-500 to-yellow-600",
  pop: "from-sky-400 to-cyan-500",
  mysterious: "from-violet-600 to-indigo-700",
  crystal: "from-cyan-400 to-blue-500",
  dramatic: "from-fuchsia-600 to-purple-700",
  whisper: "from-emerald-400 to-teal-500",
  moody: "from-slate-600 to-indigo-900",
};

// 診断結果表示中のページ全体の背景（タイプ色を薄く敷く。白カードが映える濃度に留める）。
// VTYPE_STYLE（カードの濃いグラデ）と対で管理し、色相を一致させる。
export const VTYPE_PAGE_BG: Record<string, string> = {
  rock: "from-rose-100 via-orange-50 to-orange-100",
  groovy: "from-amber-100 via-yellow-50 to-yellow-100",
  pop: "from-sky-100 via-cyan-50 to-cyan-100",
  mysterious: "from-violet-200 via-indigo-50 to-indigo-100",
  crystal: "from-cyan-100 via-sky-50 to-blue-100",
  dramatic: "from-fuchsia-100 via-purple-50 to-purple-100",
  whisper: "from-emerald-100 via-teal-50 to-teal-100",
  moody: "from-slate-200 via-indigo-100 to-indigo-200",
};

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
  groovy: { name: "Groovy Voice", emoji: "🎙", desc: "太く温かい地声成分。厚みのある低音で聴かせる声。" },
  pop: { name: "Pop Voice", emoji: "🌤", desc: "自然体で親しみやすい、軽やかで明るい地声成分の声。" },
  mysterious: { name: "Mysterious Voice", emoji: "🌒", desc: "翳りのある落ち着いた地声に息が混ざる、静かでも記憶に残る声。" },
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
