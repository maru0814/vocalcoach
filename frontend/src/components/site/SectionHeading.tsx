import { ReactNode } from "react";

/** 見出し内のマーカー下線（蛍光ペン風）。tone="dark" は暗面用。 */
export function Marker({ children, tone = "light" }: { children: ReactNode; tone?: "light" | "dark" }) {
  return (
    <span className="relative inline-block">
      <span
        className={`absolute inset-x-0 bottom-[0.06em] h-[0.36em] rounded-full ${
          tone === "dark" ? "bg-brand-500/60" : "bg-gradient-to-r from-brand-200 to-pink-200"
        }`}
        aria-hidden
      />
      <span className="relative">{children}</span>
    </span>
  );
}

/**
 * eyebrow → h2 → sub の3段リズム見出し（docs/55 §5-4）。
 */
export function SectionHeading({
  eyebrow,
  title,
  sub,
  dark = false,
  className = "",
}: {
  eyebrow?: string;
  title: ReactNode;
  sub?: ReactNode;
  dark?: boolean;
  className?: string;
}) {
  return (
    <div className={`text-center ${className}`}>
      {eyebrow && (
        <p className={`text-xs font-bold tracking-[0.25em] ${dark ? "text-brand-200" : "text-brand-600"}`}>
          {eyebrow}
        </p>
      )}
      <h2 className={`mt-2 text-2xl font-black sm:text-4xl ${dark ? "text-white" : "text-slate-800"}`}>
        {title}
      </h2>
      {sub && (
        <p className={`mx-auto mt-3 max-w-2xl text-sm sm:text-base ${dark ? "text-white/80" : "text-slate-600"}`}>
          {sub}
        </p>
      )}
    </div>
  );
}
