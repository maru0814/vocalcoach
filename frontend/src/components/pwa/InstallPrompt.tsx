"use client";

import { useEffect, useState } from "react";
import { isStandalone } from "@/lib/push";

/** Chrome系の beforeinstallprompt イベント型（型定義が標準に無いため最小定義）。 */
type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "pwa_install_dismissed_at";
const DISMISS_DAYS = 7;

function recentlyDismissed(): boolean {
  if (typeof window === "undefined") return true;
  const raw = window.localStorage.getItem(DISMISS_KEY);
  if (!raw) return false;
  const ts = Number(raw);
  if (!ts) return false;
  return Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000;
}

function isIos(): boolean {
  if (typeof window === "undefined") return false;
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

/**
 * インストール導線バナー＋iOS手順シート（docs/74 SCR-01 / SCR-02）。
 * - Android/Chrome系: beforeinstallprompt を捕捉して「追加する」で prompt()。
 * - iOS/Safari: 非対応なので「共有→ホーム画面に追加」の手順シートを出す。
 * - standalone起動時・7日以内に閉じた場合は出さない。自動ポップアップはしない。
 */
export default function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [iosSheet, setIosSheet] = useState(false);

  useEffect(() => {
    if (isStandalone() || recentlyDismissed()) return;

    // Android/Chrome系
    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", onBip);

    // iOS Safari は beforeinstallprompt 非対応 → 手順案内でバナーだけ出す
    if (isIos()) setVisible(true);

    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  const dismiss = () => {
    setVisible(false);
    setIosSheet(false);
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      /* localStorage不可でも動作継続 */
    }
  };

  const add = async () => {
    if (deferred) {
      await deferred.prompt();
      await deferred.userChoice;
      setDeferred(null);
      setVisible(false);
    } else if (isIos()) {
      setIosSheet(true);
    }
  };

  if (!visible) return null;

  return (
    <>
      <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-3 border-t bg-white px-4 py-3 shadow-lg [padding-bottom:env(safe-area-inset-bottom)]">
        <img src="/icons/icon-192.png" alt="" aria-hidden className="h-10 w-10 shrink-0 rounded-xl" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-slate-800">ソラ先生をアプリに追加</p>
          <p className="truncate text-xs text-slate-500">
            ワンタップ起動・練習リマインド・オフラインでも開ける
          </p>
        </div>
        <button
          onClick={add}
          className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
        >
          追加
        </button>
        <button onClick={dismiss} aria-label="あとで" className="shrink-0 px-1 text-slate-400">
          ×
        </button>
      </div>

      {iosSheet && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-label="ホーム画面への追加方法（iPhone）"
          onClick={dismiss}
        >
          <div
            className="w-full rounded-t-2xl bg-white p-5 [padding-bottom:calc(1.25rem+env(safe-area-inset-bottom))]"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-1 text-lg font-bold text-slate-800">
              ソラ先生をホーム画面に
            </h2>
            <p className="mb-3 text-sm text-slate-600">
              アプリのように1タップで開けて、練習を続けやすくなります。
            </p>
            <ol className="space-y-2 text-sm text-slate-700">
              <li>1. 画面下の共有アイコン（□に↑）をタップ</li>
              <li>2. メニューを下にスクロールして「ホーム画面に追加」</li>
              <li>3. 右上の「追加」をタップ</li>
            </ol>
            <p className="mt-3 text-xs text-slate-500">
              追加すると、練習リマインド通知も受け取れるようになります。
            </p>
            <button
              onClick={dismiss}
              className="mt-4 w-full rounded bg-slate-100 py-2 text-sm font-medium text-slate-700"
            >
              閉じる
            </button>
          </div>
        </div>
      )}
    </>
  );
}
