"use client";

import { useEffect, useState } from "react";

/**
 * オフライン時に上部へ控えめなバーを出す（docs/74 SCR-04）。
 * エラー(rose)ではなく「一時的な状態」として中立トーン。オンライン復帰で自動的に消える。
 */
export default function OfflineBar() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;
  return (
    <div
      role="status"
      className="sticky top-0 z-50 w-full bg-slate-800 px-4 py-2 text-center text-xs text-white"
    >
      オフラインです。解析にはネット接続が必要です。
    </div>
  );
}
