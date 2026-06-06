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
