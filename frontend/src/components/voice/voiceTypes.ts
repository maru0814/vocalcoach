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
