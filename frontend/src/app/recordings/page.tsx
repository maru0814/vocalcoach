"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listRecordings, RecordingListItem } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { AppHeader } from "@/components/AppHeader";

export default function RecordingsPage() {
  const [items, setItems] = useState<RecordingListItem[]>([]);
  const [lockedCount, setLockedCount] = useState(0);
  const [error, setError] = useState("");
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await listRecordings();
        setItems(data.items);
        setLockedCount(data.locked_count);
      } catch (err) {
        setError(err instanceof Error ? err.message : "一覧取得に失敗しました");
      }
    })();
  }, []);

  return (
    <>
    <AppHeader />
    <div className="mx-auto max-w-3xl space-y-4 px-5 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">評価履歴一覧</h1>
        <Link className="rounded bg-blue-600 px-4 py-2 text-white" href="/recordings/new">
          新規アップロード
        </Link>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <ul className="space-y-3">
        {items.map((item) => (
          <li className="rounded bg-white p-4 shadow" key={item.id}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold">{item.title}</p>
                <p className="text-sm text-gray-500">
                  {new Date(item.created_at).toLocaleString("ja-JP")}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm">総合: {item.total_score ?? "-"}</p>
                <Link className="text-blue-700 underline" href={`/recordings/${item.id}`}>
                  詳細
                </Link>
              </div>
            </div>
          </li>
        ))}
        {lockedCount > 0 ? (
          <li className="rounded border border-dashed bg-gray-50 p-4 text-center text-sm">
            🔒 ほか {lockedCount} 件の録音は
            <button className="mx-1 text-blue-700 underline" onClick={() => setShowUpgrade(true)}>
              プレミアム
            </button>
            で見られます
          </li>
        ) : null}
      </ul>
      {showUpgrade ? <UpgradeModal source="history" onClose={() => setShowUpgrade(false)} /> : null}
    </div>
    </>
  );
}
