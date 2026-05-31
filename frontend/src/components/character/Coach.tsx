// ボーカルトレーナーのキャラクター「ソラ先生」。サービス全体で共通利用する。
export const COACH_NAME = "ソラ先生";
export const COACH_ROLE = "AIボーカルトレーナー";
export const SERVICE_NAME = "AIボーカルトレーナー ソラ先生";

/**
 * 先生らしいアバター：メガネ・ヘッドセットマイク・シャツの襟つきの、
 * 親しみやすいボーカルトレーナー。
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
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        {/* シャツ＋襟（先生感） */}
        <path d="M14 44v-3a10 10 0 0 1 20 0v3z" fill="#5b6b8c" />
        <path d="M24 36l-5 3 5 4 5-4z" fill="#ffffff" />
        <path d="M24 37l-2.2 2.4L24 43l2.2-3.6z" fill="#d65a7a" />
        {/* 首 */}
        <rect x="21" y="33" width="6" height="6" rx="3" fill="#f6c89a" />
        {/* 顔 */}
        <circle cx="24" cy="24" r="12.5" fill="#ffe2c4" />
        {/* 髪（七三・きっちり） */}
        <path d="M11.5 23c0-7.2 5.6-12 12.5-12s12.5 4.8 12.5 12c0-2.2-1.4-3.6-3-4-1.3 4-13.5 5.4-18.2 1.3-1.4.8-3.8 1.4-3.8 2.7z" fill="#5b3a29" />
        <path d="M23 11.2c4 .2 7 1.8 9 4.2-2.5-1.2-6-1.7-9-1.4z" fill="#6b4632" />
        {/* ヘッドセットのバンド */}
        <path d="M10.2 24a13.8 13.8 0 0 1 27.6 0" stroke="#3f4960" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        {/* イヤーパッド（左右） */}
        <rect x="8.2" y="22.5" width="4.4" height="7.5" rx="2.2" fill="#3f4960" />
        <rect x="35.4" y="22.5" width="4.4" height="7.5" rx="2.2" fill="#3f4960" />
        {/* ブームマイク（口元へ） */}
        <path d="M11 30c0 5 3 8 8 9" stroke="#3f4960" strokeWidth="1.8" fill="none" strokeLinecap="round" />
        <circle cx="19.5" cy="39.2" r="1.8" fill="#3f4960" />
        {/* メガネ */}
        <circle cx="19" cy="24" r="3.6" fill="#ffffff" fillOpacity="0.35" stroke="#3a3f4a" strokeWidth="1.4" />
        <circle cx="29" cy="24" r="3.6" fill="#ffffff" fillOpacity="0.35" stroke="#3a3f4a" strokeWidth="1.4" />
        <path d="M22.6 24h2.8M32.6 23.5l3 .4M15.4 23.5l-3 .4" stroke="#3a3f4a" strokeWidth="1.3" strokeLinecap="round" />
        {/* 目 */}
        <circle cx="19" cy="24.3" r="1.5" fill="#4a3328" />
        <circle cx="29" cy="24.3" r="1.5" fill="#4a3328" />
        {/* ほっぺ */}
        <circle cx="16" cy="28.5" r="1.6" fill="#ff9d8a" opacity="0.5" />
        <circle cx="32" cy="28.5" r="1.6" fill="#ff9d8a" opacity="0.5" />
        {/* 笑顔 */}
        <path d="M20.5 29.5q3.5 3 7 0" stroke="#4a3328" strokeWidth="1.7" fill="none" strokeLinecap="round" />
      </svg>
    </span>
  );
}
