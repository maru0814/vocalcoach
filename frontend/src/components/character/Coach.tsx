// ボーカルトレーナーのキャラクター「ソラ先生」。サービス全体で共通利用する。
import Image from "next/image";

export const COACH_NAME = "ソラ先生";
export const COACH_ROLE = "AIボーカルトレーナー";
export const SERVICE_NAME = "AIボーカルトレーナー ソラ先生";

/** ポーズライブラリ（docs/56 §3-6）。同一画面に同じポーズを2回出さない。 */
export type CoachPose = "singing" | "explain" | "cheer" | "clap" | "thinking" | "bow";

/**
 * ソラ先生のアバター。サービス共通のキャラクター画像（チビ調）を円形で表示する。
 * pose 省略時は従来の顔アイコン（`/brand/sora-icon.png`）、指定時は `/brand/poses/` のポーズ差分。
 */
export function CoachAvatar({
  size = 36,
  ring = false,
  pose,
}: {
  size?: number;
  ring?: boolean;
  pose?: CoachPose;
}) {
  const src = pose ? `/brand/poses/${pose}.png` : "/brand/sora-icon.png";
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-white shadow-soft ${
        ring ? "ring-2 ring-white" : ""
      }`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <Image
        src={src}
        alt=""
        width={size}
        height={size}
        className="h-full w-full object-cover"
        priority={size >= 40}
      />
    </span>
  );
}
