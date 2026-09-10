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

// primary の「構造」（色以外）。tone（塗り・文字・影）を差し替えても物理感は共通に保つ
const PRIMARY_STRUCTURE =
  "hover:brightness-110 active:translate-y-[3px] " +
  "disabled:opacity-40 disabled:shadow-none disabled:active:translate-y-0";

const VARIANTS: Record<Variant, string> = {
  // 下辺影で「押せる物理感」。active で3px沈み影が1pxへ。
  primary:
    "bg-brand-600 text-white shadow-[0_4px_0_#5b21b6] active:shadow-[0_1px_0_#5b21b6] " +
    PRIMARY_STRUCTURE,
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
  /** primary の色（塗り・文字・3D影）だけ差し替える。声タイプ別テーマ（docs/72）用。
   *  完全リテラルのクラス文字列（例: VTYPE_THEME[*].button）を渡す。 */
  tone?: string;
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
  const { variant = "primary", size = "md", tone, className = "", children } = props;
  const variantCls = variant === "primary" && tone ? `${tone} ${PRIMARY_STRUCTURE}` : VARIANTS[variant];
  const cls = `${BASE} ${SIZES[size]} ${variantCls} ${className}`;
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
