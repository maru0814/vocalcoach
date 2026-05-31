// ボーカルコーチのキャラクター「ソラ先生」。サービス全体で共通利用する。
export const COACH_NAME = "ソラ先生";
export const COACH_ROLE = "AIボーカルコーチ";

/** ヘッドホンをつけた、親しみやすい先生キャラのアバター */
export function CoachAvatar({ size = 36, ring = false }: { size?: number; ring?: boolean }) {
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-gradient shadow-soft ${
        ring ? "ring-2 ring-white" : ""
      }`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        {/* 顔 */}
        <circle cx="24" cy="26" r="12.5" fill="#ffe2c4" />
        {/* 前髪 */}
        <path d="M12 24c0-7 5.5-12 12-12s12 5 12 12c0-2-3.5-4-7-4-2 0-3 1-5 1s-3-1-5-1c-3.5 0-7 2-7 4z" fill="#6b3f2a" />
        {/* ヘッドホンのバンド */}
        <path d="M10.5 25a13.5 13.5 0 0 1 27 0" stroke="#ffffff" strokeWidth="2.6" fill="none" strokeLinecap="round" />
        {/* イヤーカップ */}
        <rect x="8.5" y="23" width="4.5" height="8" rx="2.2" fill="#ffffff" />
        <rect x="35" y="23" width="4.5" height="8" rx="2.2" fill="#ffffff" />
        {/* 目 */}
        <circle cx="20" cy="26" r="1.7" fill="#4a3328" />
        <circle cx="28" cy="26" r="1.7" fill="#4a3328" />
        {/* ほっぺ */}
        <circle cx="17.5" cy="29.5" r="1.6" fill="#ff9d8a" opacity="0.55" />
        <circle cx="30.5" cy="29.5" r="1.6" fill="#ff9d8a" opacity="0.55" />
        {/* 笑顔 */}
        <path d="M20.5 30.5q3.5 3 7 0" stroke="#4a3328" strokeWidth="1.7" fill="none" strokeLinecap="round" />
      </svg>
    </span>
  );
}
