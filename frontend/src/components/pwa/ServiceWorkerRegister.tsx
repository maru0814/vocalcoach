"use client";

import { useEffect } from "react";

/**
 * /sw.js を登録する（docs/75 §5）。SW登録が失敗しても通常のWebとして動作する
 * ＝プログレッシブ・エンハンスメント（AC-08）。UIは描かない。
 *
 * dev では登録しない: dev のチャンクURLは安定名（中身だけ変わる）なので、
 * SWのCacheFirstが古いバンドルを配り続けてしまう。既存登録も解除して
 * 汚染済みのローカル環境を自己修復する。
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    if (process.env.NODE_ENV !== "production") {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((reg) => reg.unregister());
      });
      if ("caches" in window) {
        caches.keys().then((keys) => {
          keys.filter((k) => k.startsWith("sora-shell")).forEach((k) => caches.delete(k));
        });
      }
      return;
    }

    // 新SWが有効化されたら一度だけリロードして新シェルに載せ替える。
    // 初回インストール時の clients.claim() でも controllerchange が飛ぶため、
    // 「もともと制御下にあったページ」だけをリロード対象にする（無限ループ防止）。
    let hadController = Boolean(navigator.serviceWorker.controller);
    const onControllerChange = () => {
      if (!hadController) {
        hadController = true;
        return;
      }
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);

    // タブが長寿命でも更新を拾えるよう、復帰時に更新チェックする。
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      navigator.serviceWorker.getRegistration().then((reg) => reg?.update().catch(() => {}));
    };
    document.addEventListener("visibilitychange", onVisible);

    const onLoad = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        /* 登録失敗は握りつぶす（Web機能は継続） */
      });
    };
    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad);
    return () => {
      window.removeEventListener("load", onLoad);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
  return null;
}
