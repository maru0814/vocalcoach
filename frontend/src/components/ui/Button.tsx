import Link from "next/link";
import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

/**
 * 唯一のボタン型（docs/61 §3-4・Duolingo型）。
 * LP/アプリ内のCTAはすべてこれを使う。独自クラスでのボタン作成は禁止。
 * 5状態: default / hover / active(沈む) / focus-visible / disabled。
 */
const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full font-bold " +
  "transition-[transform,box-shadow,background-color,filter] duration-100 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2";

const SIZES = {
  md: "px-7 py-3.5",
  sm: "px-5 py-2 text-sm",
} as const;

const VARIANTS: Record<Variant, string> = {
  // 下辺影で「押せる物理感」。active で3px沈み影が1pxへ。
  primary:
    "bg-brand-600 text-white shadow-[0_4px_0_#5b21b6] hover:brightness-110 " +
    "active:translate-y-[3px] active:shadow-[0_1px_0_#5b21b6] " +
    "disabled:opacity-40 disabled:shadow-none disabled:active:translate-y-0",
  secondary:
    "border border-slate-200 bg-white text-slate-800 shadow-[0_4px_0_#cbd5e1] hover:bg-slate-50 " +
    "active:translate-y-[3px] active:shadow-[0_1px_0_#cbd5e1] " +
    "disabled:opacity-40 disabled:shadow-none disabled:active:translate-y-0",
  ghost:
    "bg-transparent text-brand-700 hover:bg-brand-50 active:translate-y-[1px] disabled:opacity-40",
};

type CommonProps = {
  variant?: Variant;
  size?: keyof typeof SIZES;
  className?: string;
  children: ReactNode;
};

type AsLink = CommonProps & { href: string; disabled?: never; type?: never; onClick?: never };
type AsButton = CommonProps & {
  href?: never;
  disabled?: boolean;
  type?: "button" | "submit";
  onClick?: () => void;
};

export function Button(props: AsLink | AsButton) {
  const { variant = "primary", size = "md", className = "", children } = props;
  const cls = `${BASE} ${SIZES[size]} ${VARIANTS[variant]} ${className}`;
  if ("href" in props && props.href) {
    return (
      <Link href={props.href} className={cls}>
        {children}
      </Link>
    );
  }
  const { disabled, type = "button", onClick } = props as AsButton;
  return (
    <button type={type} className={cls} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}
