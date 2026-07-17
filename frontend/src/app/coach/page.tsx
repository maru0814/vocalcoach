"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createCoachSession,
  listCoachSessions,
  renameCoachSession,
  SessionSummary,
} from "@/lib/api";
import { redirectToLoginIfAuthError } from "@/lib/authRedirect";
import { BrandWordmark, Pill } from "@/components/brand/Brand";
import { PremiumWidget } from "@/components/PremiumWidget";
import { CoachAvatar } from "@/components/character/Coach";
import { StageDecor } from "@/components/site/Stage";
import { Icon, IconChip } from "@/components/site/IconChip";

const PHASE_LABEL: Record<string, string> = {
  A: "曲を決める", B: "課題を見つける", C: "基礎練中", D: "練習チェック", E: "再録音", done: "完了",
};
const PHASE_TONE: Record<string, "brand" | "amber" | "emerald" | "slate"> = {
  A: "slate", B: "brand", C: "brand", D: "brand", E: "brand", done: "emerald",
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
      } catch (err) {
        if (redirectToLoginIfAuthError(err, router)) return;
        setError("読み込みに失敗しました。通信状態を確認して、もう一度お試しください。");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function startNew() {
    setCreating(true);
    try {
      // 未着手セッションは一覧に出ないため、作成レスポンスのIDへ直接遷移する
      const created = await createCoachSession();
      if (created.session_id == null) throw new Error("session_id missing in create response");
      router.push(`/coach/${created.session_id}`);
    } catch (err) {
      if (redirectToLoginIfAuthError(err, router)) return;
      setError("セッションを作成できませんでした。時間をおいてもう一度お試しください。");
      setCreating(false);
    }
  }

  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  function beginEdit(s: SessionSummary) {
    setEditingId(s.id);
    setDraft(s.song_title || `レッスン #${s.id}`);
    setTimeout(() => inputRef.current?.select(), 0);
  }

  async function commitEdit(id: number) {
    const name = draft.trim();
    setEditingId(null);
    if (!name) return;
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, song_title: name } : s)));
    try {
      await renameCoachSession(id, name);
    } catch {
      setError("名前の変更に失敗しました。");
      setSessions(await listCoachSessions().catch(() => sessions));
    }
  }

  return (
    <div className="bg-studio min-h-[100dvh]">
      <header className="mx-auto flex max-w-2xl items-center justify-between gap-3 p-5">
        <BrandWordmark size={40} />
        <div className="flex items-center gap-4">
          <PremiumWidget />
          <Link href="/login" className="text-sm font-medium text-slate-500 hover:text-brand-600">
            ログアウト
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5 pb-16">
        {/* ヒーローCTA（今日のステージへ docs/55 Phase 3） */}
        <button
          onClick={startNew}
          disabled={creating}
          className="group bg-stage grain relative w-full overflow-hidden rounded-2xl p-6 text-left text-white shadow-soft transition hover:shadow-card-2 active:scale-[0.99] disabled:opacity-70"
        >
          <StageDecor notes={false} />
          <div className="relative z-10 flex items-center gap-4">
            <IconChip icon="mic" size={56} className="shadow-glow-neon" />
            <div>
              <div className="text-lg font-black">
                {creating ? "準備しています…" : "新しいレッスンを始める"}
              </div>
              <div className="text-sm text-white/80">曲を選んで、歌って、フィードバックをもらおう</div>
            </div>
            <span className="ml-auto text-2xl opacity-80 transition group-hover:translate-x-1">→</span>
          </div>
        </button>

        {/* 声タイプ診断（別機能・いつでも） */}
        <Link
          href="/voice-type"
          className="group flex items-center gap-3 rounded-2xl bg-white/80 p-4 shadow-card ring-1 ring-brand-100 transition hover:-translate-y-0.5 hover:shadow-card-2"
        >
          <IconChip icon="search" size={48} />
          <div className="min-w-0 flex-1">
            <div className="font-bold text-slate-800">声タイプ診断</div>
            <div className="text-xs text-slate-500">15秒歌うだけ。8タイプから診断＆シェア（いつでもOK）</div>
          </div>
          <span className="text-xl text-brand-400 transition group-hover:translate-x-1">→</span>
        </Link>

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
          <div className="glass rounded-2xl p-10 text-center shadow-card">
            <div className="animate-floaty mx-auto mb-3 inline-flex">
              <CoachAvatar size={64} ring />
            </div>
            <div className="mb-3 flex items-end justify-center gap-1" aria-hidden>
              {[0, 1, 2, 3, 4].map((i) => (
                <span
                  key={i}
                  className="block w-1.5 origin-bottom animate-eq rounded-full bg-brand-300"
                  style={{ height: 14, animationDelay: `${i * 0.12}s` }}
                />
              ))}
            </div>
            <p className="font-bold text-slate-700">まだレッスンがありません</p>
            <p className="mt-1 text-sm text-slate-500">ソラ先生が待っています。上のボタンから、最初のレッスンを始めましょう。</p>
          </div>
        ) : (
          <ul className="space-y-3">
            {sessions.map((s) => (
              <li key={s.id} className="animate-fade-in-up">
                <div className="glass flex items-center gap-3 rounded-2xl p-4 shadow-card transition hover:-translate-y-0.5 hover:shadow-card-2">
                  <Link href={`/coach/${s.id}`} className="shrink-0">
                    <IconChip icon="note" size={48} />
                  </Link>
                  <div className="min-w-0 flex-1">
                    {editingId === s.id ? (
                      <input
                        ref={inputRef}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={() => commitEdit(s.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitEdit(s.id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        className="w-full rounded-lg border border-brand-300 bg-white px-2 py-1 text-sm font-bold text-slate-800 outline-none focus:shadow-glow"
                        maxLength={200}
                      />
                    ) : (
                      <Link href={`/coach/${s.id}`} className="block">
                        <div className="truncate font-bold text-slate-800">
                          {s.song_title || `レッスン #${s.id}`}
                        </div>
                        <div className="text-xs text-slate-400">
                          {new Date(s.updated_at).toLocaleString("ja-JP", {
                            month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
                          })}
                        </div>
                      </Link>
                    )}
                  </div>
                  {editingId !== s.id && (
                    <>
                      <button
                        onClick={() => beginEdit(s)}
                        aria-label="名前を変更"
                        title="名前を変更"
                        className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition hover:bg-white hover:text-brand-600"
                      >
                        
                      </button>
                      <Link href={`/coach/${s.id}`}>
                        <Pill tone={PHASE_TONE[s.phase] || "slate"}>{PHASE_LABEL[s.phase] || s.phase}</Pill>
                      </Link>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
