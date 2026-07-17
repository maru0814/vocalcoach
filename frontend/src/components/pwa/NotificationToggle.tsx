"use client";

import { useEffect, useState } from "react";
import {
  disablePush,
  enablePush,
  isStandalone,
  isSubscribed,
  pushSupported,
  VAPID_PUBLIC_KEY,
} from "@/lib/push";

/**
 * 練習リマインド通知のON/OFF（docs/74 SCR-03）。6状態を網羅:
 * default / loading / success / error / denied / unsupported。
 * 許諾は必ずこのトグル操作起点（ページ読込直後に自動要求しない＝AC-05）。
 */
type UiState = "default" | "loading" | "error" | "denied" | "unsupported";

export default function NotificationToggle() {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [on, setOn] = useState(false);
  const [state, setState] = useState<UiState>("default");
  const [message, setMessage] = useState("");
  const [iosNeedsInstall, setIosNeedsInstall] = useState(false);

  useEffect(() => {
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
    // iOSは「ホーム画面に追加したPWA」でのみWeb Push可（iOS16.4+）。未追加なら導線側へ委ねる。
    if (isIos && !isStandalone()) {
      setIosNeedsInstall(true);
      setSupported(false);
      return;
    }
    const ok = pushSupported() && !!VAPID_PUBLIC_KEY;
    setSupported(ok);
    if (!ok) return;
    if (Notification.permission === "denied") setState("denied");
    isSubscribed().then(setOn);
  }, []);

  const toggle = async () => {
    if (state === "loading") return;
    setMessage("");
    setState("loading");
    try {
      if (!on) {
        const result = await enablePush();
        if (result === "denied") {
          setState("denied");
          setOn(false);
          return;
        }
        setOn(true);
        setState("default");
        setMessage("通知をオンにしました");
      } else {
        await disablePush();
        setOn(false);
        setState("default");
        setMessage("通知をオフにしました");
      }
    } catch {
      setState("error");
      setOn(false);
      setMessage("通知の設定に失敗しました。時間をおいてお試しください");
    }
  };

  // --- unsupported 系はセクション自体を出さない or 案内のみ ---
  if (supported === null) return null; // 判定中は描かない（ちらつき防止）
  if (iosNeedsInstall) {
    return (
      <section className="space-y-2 rounded bg-white p-5 shadow">
        <h2 className="font-semibold">練習リマインド通知</h2>
        <p className="text-sm text-slate-600">
          この端末では、まずホーム画面に追加すると通知が使えます。
        </p>
      </section>
    );
  }
  if (!supported) return null; // Push非対応ブラウザ: 何も出さない（機能デグレなし）

  const denied = state === "denied";
  return (
    <section className="space-y-3 rounded bg-white p-5 shadow">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold">練習リマインド通知</h2>
          <p className="text-xs text-slate-500">
            最後の練習から少し空いたら、そっとお知らせします（1日1回まで）。
          </p>
        </div>
        <button
          role="switch"
          aria-checked={on}
          aria-label="練習リマインド通知"
          disabled={denied || state === "loading"}
          onClick={toggle}
          className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40 ${
            on ? "bg-blue-600" : "bg-slate-300"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
              on ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {state === "loading" && <p className="text-xs text-slate-400">設定中…</p>}
      {denied && (
        <p className="text-xs text-slate-500">
          ブラウザの設定で通知が拒否されています。サイトの設定から許可してください。
        </p>
      )}
      {state === "error" && <p className="text-xs text-red-600">{message}</p>}
      {state === "default" && message && (
        <p className="text-xs text-emerald-600">{message}</p>
      )}
    </section>
  );
}
