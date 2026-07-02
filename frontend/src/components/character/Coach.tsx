// ボーカルトレーナーのキャラクター「ソラ先生」。サービス全体で共通利用する。
import Image from "next/image";

export const COACH_NAME = "ソラ先生";
export const COACH_ROLE = "AIボーカルトレーナー";
export const SERVICE_NAME = "AIボーカルトレーナー ソラ先生";

/**
 * ソラ先生のアバター。サービス共通のキャラクター画像（チビ調）を円形で表示する。
 * 画像は声タイプ図鑑・SNSと同じ絵柄で統一（`/brand/sora-icon.png`）。
 */
export function CoachAvatar({ size = 36, ring = false }: { size?: number; ring?: boolean }) {
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-gradient shadow-soft ${
        ring ? "ring-2 ring-white" : ""
      }`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <Image
        src="/brand/sora-icon.png"
        alt=""
        width={size}
        height={size}
        className="h-full w-full object-cover"
        priority={size >= 40}
      />
    </span>
  );
}
