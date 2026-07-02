"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { listRecordings, RecordingListItem } from "@/lib/api";
import { redirectToLoginIfAuthError } from "@/lib/authRedirect";
import UpgradeModal from "@/components/UpgradeModal";
import { AppHeader } from "@/components/AppHeader";

export default function RecordingsPage() {
  const router = useRouter();
  const [items, setItems] = useState<RecordingListItem[]>([]);
  const [lockedCount, setLockedCount] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [showUpgrade, setShowUpgrade] = useState(false);

  const load = useCallback(async () => {
    setStatus("loading");
    setError("");
    try {
      const data = await listRecordings();
      setItems(data.items);
      setLockedCount(data.locked_count);
      setStatus("ready");
    } catch (err) {
      if (redirectToLoginIfAuthError(err, router)) return;
      const msg = err instanceof Error ? err.message : "";
      // ネットワーク失敗の生メッセージ（"Failed to fetch"）は出さず、次の手を示す
      setError(
        !msg || /failed to fetch|networkerror/i.test(msg)
          ? "履歴を読み込めませんでした。通信状態を確かめて、もう一度お試しください。"
          : msg,
      );
      setStatus("error");
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  const isEmpty = status === "ready" && items.length === 0 && lockedCount === 0;

  return (
    <div className="bg-studio min-h-[100dvh]">
      <AppHeader />
      <div className="mx-auto max-w-3xl space-y-5 px-5 py-6">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl font-black text-slate-800">評価アーカイブ</h1>
          {/* 単発アップロードは残すが補助に格下げ（主役は coach・docs/49 SCR-IA-3） */}
          <Link
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-600 transition active:scale-95"
            href="/recordings/new"
          >
            ＋ 単発アップロード
          </Link>
        </div>

        {/* coach 誘導バナー（圧の弱い補助導線・docs/49） */}
        <Link
          href="/coach"
          className="glass flex items-center gap-3 rounded-2xl p-4 shadow-card ring-1 ring-brand-100 transition hover:shadow-soft"
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-2xl text-white shadow-soft">
            🎤
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold text-slate-800">録音は「レッスン」からどうぞ</div>
            <div className="text-xs text-slate-500">会話しながらFBをもらえます。ここは過去の評価を見返す場所です。</div>
          </div>
          <span className="text-lg font-bold text-brand-600">→</span>
        </Link>

        {/* loading */}
        {status === "loading" && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="shimmer h-20 rounded-2xl bg-white/60" />
            ))}
          </div>
        )}

        {/* error（再試行つき） */}
        {status === "error" && (
          <div className="glass rounded-3xl p-8 text-center shadow-card">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 text-3xl">
              😢
            </div>
            <p className="font-bold text-slate-700">{error}</p>
            <button
              onClick={load}
              className="mt-4 rounded-full bg-brand-gradient px-6 py-2.5 text-sm font-bold text-white shadow-soft transition active:scale-95"
            >
              再試行する
            </button>
          </div>
        )}

        {/* empty */}
        {isEmpty && (
          <div className="glass rounded-3xl p-10 text-center shadow-card">
            <div className="animate-floaty mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-gradient text-3xl shadow-soft">
              🎶
            </div>
            <p className="font-bold text-slate-700">まだ評価がありません</p>
            <p className="mt-1 text-sm text-slate-500">まずは「レッスン」で1曲歌うと、ここに評価が並びます。</p>
            <Link
              href="/coach"
              className="mt-4 inline-flex rounded-full bg-brand-gradient px-6 py-2.5 text-sm font-bold text-white shadow-soft transition active:scale-95"
            >
              レッスンを始める →
            </Link>
          </div>
        )}

        {/* success（一覧） */}
        {status === "ready" && !isEmpty && (
          <ul className="space-y-3">
            {items.map((item) => (
              <li key={item.id} className="animate-fade-in-up">
                <Link
                  href={`/recordings/${item.id}`}
                  className="glass flex items-center justify-between gap-4 rounded-2xl p-4 shadow-card transition hover:shadow-soft"
                >
                  <div className="min-w-0">
                    <p className="truncate font-bold text-slate-800">{item.title}</p>
                    <p className="text-xs text-slate-400">
                      {new Date(item.created_at).toLocaleString("ja-JP")}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-lg font-black text-brand-600">{item.total_score ?? "—"}</p>
                    <p className="text-[11px] text-slate-400">総合</p>
                  </div>
                </Link>
              </li>
            ))}
            {lockedCount > 0 && (
              <li className="rounded-2xl border border-dashed border-brand-200 bg-white/60 p-4 text-center text-sm text-slate-600">
                🔒 ほか {lockedCount} 件の録音は
                <button
                  className="mx-1 font-bold text-brand-600 underline-offset-2 hover:underline"
                  onClick={() => setShowUpgrade(true)}
                >
                  プレミアム
                </button>
                で見られます
              </li>
            )}
          </ul>
        )}

        {showUpgrade && <UpgradeModal source="history" onClose={() => setShowUpgrade(false)} />}
      </div>
    </div>
  );
}
