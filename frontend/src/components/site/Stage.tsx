import { ReactNode } from "react";

// 夜のステージ装飾（docs/55 §5-3）。座標は固定値＝SSRとクライアントで一致させる。
const STARS: Array<{ top: string; left: string; size: number; delay: string }> = [
  { top: "8%", left: "12%", size: 2, delay: "0s" },
  { top: "16%", left: "78%", size: 3, delay: "0.7s" },
  { top: "24%", left: "38%", size: 2, delay: "1.4s" },
  { top: "10%", left: "55%", size: 2, delay: "2.1s" },
  { top: "34%", left: "88%", size: 2, delay: "0.4s" },
  { top: "42%", left: "8%", size: 3, delay: "1.1s" },
  { top: "56%", left: "70%", size: 2, delay: "1.8s" },
  { top: "64%", left: "22%", size: 2, delay: "0.9s" },
  { top: "72%", left: "92%", size: 2, delay: "1.6s" },
  { top: "80%", left: "48%", size: 3, delay: "0.2s" },
  { top: "88%", left: "14%", size: 2, delay: "2.3s" },
  { top: "48%", left: "52%", size: 2, delay: "1.9s" },
];

const NOTES: Array<{ left: string; bottom: string; glyph: string; delay: string; duration: string }> = [
  { left: "10%", bottom: "18%", glyph: "♪", delay: "0s", duration: "5s" },
  { left: "82%", bottom: "24%", glyph: "♫", delay: "1.6s", duration: "6s" },
  { left: "58%", bottom: "12%", glyph: "♩", delay: "3.2s", duration: "5.5s" },
  { left: "30%", bottom: "8%", glyph: "♬", delay: "2.4s", duration: "6.5s" },
];

/** 暗面の環境装飾レイヤー（星のまたたき＋浮かぶ音符）。親に relative が必要。 */
export function StageDecor({ notes = true }: { notes?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden>
      {STARS.map((s, i) => (
        <span
          key={i}
          className="animate-twinkle absolute rounded-full bg-white/80"
          style={{ top: s.top, left: s.left, width: s.size, height: s.size, animationDelay: s.delay }}
        />
      ))}
      {notes &&
        NOTES.map((n, i) => (
          <span
            key={i}
            className="animate-note-float absolute text-xl text-white/25"
            style={{ left: n.left, bottom: n.bottom, animationDelay: n.delay, animationDuration: n.duration }}
          >
            {n.glyph}
          </span>
        ))}
    </div>
  );
}

/**
 * 夜のステージ面（ヒーロー・最終CTA・診断セクション用）。
 * docs/55 §5-7: 1画面に最大1〜2箇所（LPは3箇所を上限）。
 */
export function StageSection({
  children,
  className = "",
  decor = true,
}: {
  children: ReactNode;
  className?: string;
  decor?: boolean;
}) {
  return (
    <div className={`bg-stage grain relative overflow-hidden text-white ${className}`}>
      {decor && <StageDecor />}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
