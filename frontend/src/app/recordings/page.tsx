"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listRecordings, RecordingListItem } from "@/lib/api";

export default function RecordingsPage() {
  const [items, setItems] = useState<RecordingListItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await listRecordings();
        setItems(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "一覧取得に失敗しました");
      }
    })();
  }, []);

  return (
    <div className="space-y-4">
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
      </ul>
    </div>
  );
}
