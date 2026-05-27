"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getRecording, RecordingDetail } from "@/lib/api";

type Props = { params: { id: string } };

export default function RecordingDetailPage({ params }: Props) {
  const [data, setData] = useState<RecordingDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await getRecording(params.id);
        setData(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "詳細取得に失敗しました");
      }
    })();
  }, [params.id]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">評価詳細</h1>
        <Link className="text-blue-700 underline" href="/recordings">
          一覧へ戻る
        </Link>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {data ? (
        <div className="space-y-3 rounded bg-white p-5 shadow">
          <p className="font-semibold">{data.title}</p>
          <p className="text-sm text-gray-600">ステータス: {data.status}</p>
          <p className="text-sm text-gray-600">メモ: {data.note || "-"}</p>
          {data.evaluation ? (
            <div className="space-y-1">
              <p>音程: {data.evaluation.pitch_score}</p>
              <p>リズム: {data.evaluation.rhythm_score}</p>
              <p>表現: {data.evaluation.expression_score}</p>
              <p>総合: {data.evaluation.total_score}</p>
              <p className="rounded bg-gray-100 p-3 text-sm">{data.evaluation.feedback_text}</p>
            </div>
          ) : (
            <p>まだ評価が完了していません。</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
