"use client";

import { useEffect } from "react";

/**
 * /sw.js を登録する（docs/75 §5）。SW登録が失敗しても通常のWebとして動作する
 * ＝プログレッシブ・エンハンスメント（AC-08）。UIは描かない。
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    const onLoad = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        /* 登録失敗は握りつぶす（Web機能は継続） */
      });
    };
    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad);
    return () => window.removeEventListener("load", onLoad);
  }, []);
  return null;
}
