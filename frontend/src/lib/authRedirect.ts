import { isAuthError } from "./api";

/**
 * セッションの読み込みが未ログイン（401）で失敗した時、ログイン画面へ即リダイレクトする。
 * ログイン後は ?next= で元のページに戻る。リダイレクトしたら true を返すので、
 * 呼び出し側は true のときエラー表示せずそのまま return する。
 * 401以外（ネットワーク断・サーバーエラー）はログイン済みの可能性があるため飛ばさない。
 */
export function redirectToLoginIfAuthError(
  err: unknown,
  router: { replace: (href: string) => void },
): boolean {
  if (!isAuthError(err)) return false;
  const next = typeof window !== "undefined" ? window.location.pathname : "/coach";
  router.replace(`/login?next=${encodeURIComponent(next)}`);
  return true;
}
