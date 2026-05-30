"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createCoachSession, listCoachSessions, SessionSummary } from "@/lib/api";
import { BrandWordmark, Pill } from "@/components/brand/Brand";

const PHASE_LABEL: Record<string, string> = {
  A: "曲を決める", B: "課題を見つける", C: "基礎練中", D: "練習チェック", E: "再録音", done: "完了",
};
const PHASE_TONE: Record<string, "brand" | "amber" | "emerald" | "slate"> = {
  A: "slate", B: "brand", C: "amber", D: "amber", E: "brand", done: "emerald",
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
      await createCoachSession();
      const list = await listCoachSessions();
      router.push(`/coach/${list[0].id}`);
    } catch {
      setError("セッションを作成できませんでした。ログインを確認してください。");
      setCreating(false);
    }
  }

  return (
    <div className="bg-studio min-h-[100dvh]">
      <header className="mx-auto flex max-w-2xl items-center justify-between p-5">
        <BrandWordmark size={40} />
        <Link href="/login" className="text-sm font-medium text-slate-500 hover:text-brand-600">
          ログアウト
        </Link>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5 pb-16">
        {/* ヒーローCTA */}
        <button
          onClick={startNew}
          disabled={creating}
          className="group relative w-full overflow-hidden rounded-3xl bg-brand-gradient p-6 text-left text-white shadow-soft transition active:scale-[0.99] disabled:opacity-70"
        >
          <div className="absolute -right-6 -top-8 h-32 w-32 rounded-full bg-white/15 blur-2xl" />
          <div className="relative z-10 flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 text-3xl">
              {creating ? "⏳" : "🎤"}
            </span>
            <div>
              <div className="text-lg font-black">
                {creating ? "準備しています…" : "新しいレッスンを始める"}
              </div>
              <div className="text-sm text-white/80">曲を選んで、歌って、フィードバックをもらおう</div>
            </div>
            <span className="ml-auto text-2xl opacity-80 transition group-hover:translate-x-1">→</span>
          </div>
        </button>

        {error && (
          <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}

        <div className="flex items-center gap-2 px-1">
          <h2 className="text-sm font-bold text-slate-700">これまでのレッスン</h2>
          {!loading && <Pill tone="slate">{sessions.length}件</Pill>}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="shimmer h-20 rounded-2xl bg-white/60" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="glass rounded-3xl p-10 text-center shadow-card">
            <div className="animate-floaty mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient text-3xl shadow-soft">
              🎶
            </div>
            <p className="font-bold text-slate-700">まだレッスンがありません</p>
            <p className="mt-1 text-sm text-slate-500">上のボタンから、最初のレッスンを始めましょう。</p>
          </div>
        ) : (
          <ul className="space-y-3">
            {sessions.map((s) => (
              <li key={s.id} className="animate-fade-in-up">
                <Link
                  href={`/coach/${s.id}`}
                  className="glass flex items-center gap-4 rounded-2xl p-4 shadow-card transition hover:shadow-soft"
                >
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-2xl">
                    🎵
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-bold text-slate-800">
                      {s.song_title || `レッスン #${s.id}`}
                    </div>
                    <div className="text-xs text-slate-400">
                      {new Date(s.updated_at).toLocaleString("ja-JP", {
                        month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })}
                    </div>
                  </div>
                  <Pill tone={PHASE_TONE[s.phase] || "slate"}>{PHASE_LABEL[s.phase] || s.phase}</Pill>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
