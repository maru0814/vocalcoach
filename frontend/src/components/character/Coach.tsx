// ボーカルトレーナーのキャラクター「ソラ先生」。サービス全体で共通利用する。
import Image from "next/image";

export const COACH_NAME = "ソラ先生";
export const COACH_ROLE = "AIボーカルトレーナー";
export const SERVICE_NAME = "AIボーカルトレーナー ソラ先生";

/** ポーズライブラリ（docs/61 §3-6）。同一画面に同じポーズを2回出さない。 */
export type CoachPoseName = "singing" | "explain" | "cheer" | "clap" | "thinking" | "bow";

/**
 * ソラ先生のアバター。サービス共通のキャラクター画像（チビ調）を円形で表示する。
 * 画像は声タイプ図鑑・SNSと同じ絵柄で統一（`/brand/sora-icon.png`）。
 * pose を指定すると全身のポーズ画像（`/brand/poses/*.png`・640px正方）を
 * 円形トリミングなしで表示する（docs/61 §3-6）。省略時は従来の顔アイコン。
 */
export function CoachAvatar({
  size = 36,
  ring = false,
  pose,
}: {
  size?: number;
  ring?: boolean;
  pose?: CoachPoseName;
}) {
  if (pose) {
    return (
      <span
        className="relative inline-flex shrink-0 items-center justify-center"
        style={{ width: size, height: size }}
        aria-hidden
      >
        <Image
          src={`/brand/poses/${pose}.png`}
          alt=""
          width={size}
          height={size}
          className="h-full w-full object-contain drop-shadow-[0_12px_24px_rgba(15,10,46,0.35)]"
          priority={size >= 120}
        />
      </span>
    );
  }
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
