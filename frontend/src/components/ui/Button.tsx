import Link from "next/link";
import { ReactNode } from "react";

/**
 * v2の唯一のボタン型（docs/56 §3-4・Duolingo型）。
 * 単色＋下辺影、押すと沈む。CTAは必ずこれを使い、独自クラスでボタンを作らない。
 * 5状態: default / hover / active(沈む) / focus-visible / disabled
 */
type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "lg";

const VARIANT: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white shadow-[0_4px_0_0_#5b21b6] hover:bg-brand-500 active:translate-y-[3px] active:shadow-[0_1px_0_0_#5b21b6]",
  secondary:
    "bg-white text-brand-700 border border-slate-200 shadow-[0_4px_0_0_#e2e8f0] hover:bg-slate-50 active:translate-y-[3px] active:shadow-[0_1px_0_0_#e2e8f0]",
  ghost: "bg-transparent text-brand-700 hover:bg-brand-50 active:bg-brand-100",
};

const SIZE: Record<Size, string> = {
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3.5 text-base",
};

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-2xl font-bold transition-all duration-100 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 " +
  "disabled:pointer-events-none disabled:opacity-40 disabled:shadow-none";

export function Button({
  children,
  href,
  variant = "primary",
  size = "lg",
  className = "",
  onClick,
  disabled = false,
  type = "button",
}: {
  children: ReactNode;
  href?: string;
  variant?: Variant;
  size?: Size;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const cls = `${BASE} ${VARIANT[variant]} ${SIZE[size]} ${className}`;
  if (href) {
    return (
      <Link href={href} className={cls}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}
