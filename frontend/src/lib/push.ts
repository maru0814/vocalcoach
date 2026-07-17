"use client";

import { pushSubscribe, pushUnsubscribe } from "@/lib/api";

/** VAPID公開鍵（ビルド時env。未設定なら通知購読は不可＝トグルはunsupported扱い）。 */
export const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || "";

/** ブラウザがWeb Push（SW＋PushManager＋Notification）に対応しているか。 */
export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** standalone（ホーム画面に追加済み）で起動しているか。iOSの通知可否判定に使う。 */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari 独自プロパティ
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
  return output;
}

/** SW登録の準備完了を待つ（layoutで登録済み前提）。 */
async function readyRegistration(): Promise<ServiceWorkerRegistration> {
  return navigator.serviceWorker.ready;
}

/**
 * 通知をONにする。許諾要求 → 購読作成 → サーバー保存。
 * 返り値: "subscribed" | "denied"（拒否/ブロック）。失敗時は例外。
 * 呼び出しは必ずユーザー操作起点（docs/73 FR-04・AC-05）。
 */
export async function enablePush(): Promise<"subscribed" | "denied"> {
  if (!pushSupported() || !VAPID_PUBLIC_KEY) throw new Error("unsupported");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const reg = await readyRegistration();
  const existing = await reg.pushManager.getSubscription();
  const sub =
    existing ||
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY) as BufferSource,
    }));

  const json = sub.toJSON();
  await pushSubscribe({
    endpoint: sub.endpoint,
    keys: { p256dh: json.keys?.p256dh ?? "", auth: json.keys?.auth ?? "" },
  });
  return "subscribed";
}

/** 通知をOFFにする。購読解除 → サーバー無効化。 */
export async function disablePush(): Promise<void> {
  if (!pushSupported()) return;
  const reg = await readyRegistration();
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe();
  try {
    await pushUnsubscribe({ endpoint });
  } catch {
    /* サーバー側削除に失敗してもブラウザ側は解除済み。次バッチの失効掃除で回収される */
  }
}

/** 現在このブラウザで購読中か（トグル初期状態の判定）。 */
export async function isSubscribed(): Promise<boolean> {
  if (!pushSupported()) return false;
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return false;
  const sub = await reg.pushManager.getSubscription();
  return !!sub;
}
