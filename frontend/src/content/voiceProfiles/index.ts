import type { VoiceProfile } from "./types";
import { ROCK_PROFILE } from "./rock";
import { GROOVY_PROFILE } from "./groovy";
import { POP_PROFILE } from "./pop";
import { MYSTERIOUS_PROFILE } from "./mysterious";
import { CRYSTAL_PROFILE } from "./crystal";
import { DRAMATIC_PROFILE } from "./dramatic";
import { WHISPER_PROFILE } from "./whisper";
import { MOODY_PROFILE } from "./moody";

export type { VoiceProfile, ProfileSection, ProfileArtist } from "./types";

// タイプ別プロフィールのレジストリ（正本: docs/62 §6〜§13 の確定本文）。
// 全8タイプ実装済み。未制作タイプが出た場合は undefined でページ側「準備中」フォールバック（docs/62 §14）。
export const VOICE_PROFILES: Record<string, VoiceProfile | undefined> = {
  rock: ROCK_PROFILE,
  groovy: GROOVY_PROFILE,
  pop: POP_PROFILE,
  mysterious: MYSTERIOUS_PROFILE,
  crystal: CRYSTAL_PROFILE,
  dramatic: DRAMATIC_PROFILE,
  whisper: WHISPER_PROFILE,
  moody: MOODY_PROFILE,
};
