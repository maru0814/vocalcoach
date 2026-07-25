// ソラ先生ポーズの衣装差分レジストリ（docs/61 §3-6 の拡張・docs/62 §6-3）。
// 声タイプ詳細記事のセクション見出しで、タイプの世界観に合わせた衣装の
// ポーズ画像（`/brand/poses/{variant}/{pose}.png`）に切り替えるために使う。
// 画像が実在するポーズだけを列挙する。列挙にないポーズは標準衣装へフォールバック。

import type { CoachPoseName } from "./Coach";

export const COACH_POSE_VARIANTS: Record<string, readonly CoachPoseName[]> = {
  // ロック衣装（炎モチーフ）。bow は未制作のため標準衣装のまま。
  rock: ["singing", "thinking", "explain", "clap", "cheer"],
};

/** variant に pose の衣装差分画像があればその variant 名を、無ければ undefined を返す。 */
export function coachPoseVariant(
  variant: string | undefined,
  pose: CoachPoseName,
): string | undefined {
  return variant && COACH_POSE_VARIANTS[variant]?.includes(pose) ? variant : undefined;
}
