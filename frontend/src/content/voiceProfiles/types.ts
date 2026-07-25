// 声タイプ別プロフィール記事の型（正本: docs/62_デザイン仕様_声診断タイプ別プロフィール雛形.md）
// 本文中の **強調** は renderEmphasis() で <strong> に変換して描画する。

import type { IconName } from "@/components/site/IconChip";
import type { CoachPoseName } from "@/components/character/Coach";

// 各セクション共通の見出しメタ。
// icon はセクションのモチーフ（docs/61 §3-5 単色チップ）、
// pose は見出しに添えるソラ先生の全身ポーズ（docs/61 §3-6・同ページ内でポーズ重複禁止）。
// poseSrc はタイプ専用のシーン絵（`/brand/poses/<typeId>/*.jpg`）。
// 指定時は共通ポーズより優先して円形バッジで表示し、pose はフォールバック扱いになる。
type SectionBase = {
  id: string;
  nav: string; // 目次チップ用の短いラベル
  title: string;
  icon: IconName; // 見出し横のモチーフアイコン
  pose: CoachPoseName; // 見出しに添えるソラ先生のポーズ
  poseSrc?: string; // タイプ専用シーン絵（省略時は pose の共通ポーズ）
};

export type ProfileSection =
  | (SectionBase & {
      kind: "text";
      paragraphs: string[];
    })
  | (SectionBase & {
      kind: "list";
      items: string[]; // 各行も **強調** 可
      closing: string;
    });

export type ProfileArtist = {
  name: string;
  // 承認済みイラストのSVG（docs/62 §5-2 の規律で作成した静的な自前アセット）。
  // 属性名がkebab-caseのままのため、dangerouslySetInnerHTML で描画する。
  svg: string;
};

export type VoiceProfile = {
  id: string; // backend VOICE_TYPES / voiceTypes.ts の id と一致
  nameJa: string; // 例: ロックタイプ
  heroTitle: string; // §1 見出しのキャッチ部分
  lede: string; // §1 導入段落
  sections: ProfileSection[];
  artists: ProfileArtist[];
};
