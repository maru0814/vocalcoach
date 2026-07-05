import { CoachAvatar, CoachPose } from "./Coach";

/**
 * スポットライトを浴びる大型ソラ先生（docs/55 §5-6）。
 * 主役サイズ（120px+）での登場は1画面1箇所だけ。暗面（bg-stage）の上で使う。
 */
export function CoachSpotlight({
  size = 140,
  bubble,
  pose = "singing",
}: {
  size?: number;
  bubble?: string;
  pose?: CoachPose;
}) {
  return (
    <div className="relative flex flex-col items-center pt-16">
      {/* スポットライトの光条 */}
      <div
        className="pointer-events-none absolute -top-6 left-1/2 h-72 w-64 -translate-x-1/2 bg-gradient-to-b from-[#fff3cf]/35 via-[#ffe9b3]/12 to-transparent [clip-path:polygon(38%_0,62%_0,100%_100%,0_100%)]"
        aria-hidden
      />
      {bubble && (
        <div className="relative z-10 mb-4 rounded-2xl bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-card">
          {bubble}
          <span
            className="absolute -bottom-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 bg-white"
            aria-hidden
          />
        </div>
      )}
      <div className="relative z-10 animate-floaty rounded-full shadow-glow-spot">
        <CoachAvatar size={size} ring pose={pose} />
      </div>
      {/* ステージ床の照り返し */}
      <div className="mt-5 h-3 w-36 rounded-[100%] bg-neon-amber/25 blur-md" aria-hidden />
    </div>
  );
}
