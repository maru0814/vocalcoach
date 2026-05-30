"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createCoachSession, listCoachSessions, SessionSummary } from "@/lib/api";

const PHASE_LABEL: Record<string, string> = {
  A: "曲指定", B: "課題発見", C: "基礎練", D: "練習確認", E: "再録音", done: "完了",
};

export default function CoachListPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setSessions(await listCoachSessions());
      } catch {
        setError("読み込みに失敗しました。ログインしてください。");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function startNew() {
    setCreating(true);
    try {
      const res = await createCoachSession();
      const list = await listCoachSessions();
      const newest = list[0];
      router.push(`/coach/${newest.id}`);
    } catch {
      setError("セッションを作成できませんでした。ログインを確認してください。");
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">ボイストレーナー</h1>
        <Link href="/login" className="text-sm text-slate-500">ログイン</Link>
      </div>

      <button
        onClick={startNew}
        disabled={creating}
        className="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white disabled:opacity-50"
      >
        ＋ 新しいレッスンを始める
      </button>

      {error && <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />)}
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-xl border border-dashed p-8 text-center text-slate-500">
          まだレッスンがありません。<br />最初のレッスンを始めましょう。
        </div>
      ) : (
        <ul className="space-y-2">
          {sessions.map((s) => (
            <li key={s.id}>
              <Link
                href={`/coach/${s.id}`}
                className="flex items-center justify-between rounded-xl border bg-white px-4 py-3 hover:bg-slate-50"
              >
                <div>
                  <div className="font-medium">{s.song_title || "レッスン #" + s.id}</div>
                  <div className="text-xs text-slate-500">
                    {new Date(s.updated_at).toLocaleString("ja-JP")}
                  </div>
                </div>
                <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs text-indigo-700">
                  {PHASE_LABEL[s.phase] || s.phase}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
