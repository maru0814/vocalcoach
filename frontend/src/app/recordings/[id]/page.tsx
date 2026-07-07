"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getRecording, RecordingDetail } from "@/lib/api";
import { redirectToLoginIfAuthError } from "@/lib/authRedirect";
import { AppHeader } from "@/components/AppHeader";
import { Button } from "@/components/ui/Button";

type Props = { params: { id: string } };

function ScoreRow({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-white/70 px-3 py-2">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="font-black text-slate-800">{value ?? "—"}</span>
    </div>
  );
}

export default function RecordingDetailPage({ params }: Props) {
  const router = useRouter();
  const [data, setData] = useState<RecordingDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setData(await getRecording(params.id));
        setStatus("ready");
      } catch (err) {
        if (redirectToLoginIfAuthError(err, router)) return;
        const msg = err instanceof Error ? err.message : "";
        setError(
          !msg || /failed to fetch|networkerror/i.test(msg)
            ? "評価を読み込めませんでした。通信状態を確かめて、もう一度お試しください。"
            : msg,
        );
        setStatus("error");
      }
    })();
  }, [params.id, router]);

  return (
    <div className="bg-studio min-h-[100dvh]">
      <AppHeader />
      <div className="mx-auto max-w-2xl space-y-4 px-5 py-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-black text-slate-800">評価詳細</h1>
          <Link className="text-sm font-medium text-slate-500 hover:text-brand-600" href="/recordings">
            ← 評価アーカイブへ
          </Link>
        </div>

        {status === "loading" && <div className="shimmer h-48 rounded-2xl bg-white/60" />}

        {status === "error" && (
          <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>
        )}

        {status === "ready" && data && (
          <div className="glass space-y-4 rounded-2xl p-5 shadow-card">
            <div>
              <p className="text-lg font-black text-slate-800">{data.title}</p>
              <p className="text-xs text-slate-400">メモ: {data.note || "—"}</p>
            </div>

            {data.evaluation ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <ScoreRow label="音程" value={data.evaluation.pitch_score} />
                  <ScoreRow label="リズム" value={data.evaluation.rhythm_score} />
                  <ScoreRow label="表現" value={data.evaluation.expression_score} />
                  <ScoreRow label="総合" value={data.evaluation.total_score} />
                </div>
                <p className="rounded-2xl bg-brand-50 p-4 text-sm leading-relaxed text-slate-700">
                  {data.evaluation.feedback_text}
                </p>

                {/* FB直後（感情のピーク・US-02）に「次にできること」を出す（docs/35 課題3） */}
                <div className="rounded-2xl border border-brand-100 bg-white/70 p-4">
                  <p className="text-sm font-bold text-slate-700">次にできること</p>
                  <p className="font-body mt-1 text-xs leading-relaxed text-slate-500">
                    この録音について「どこで・何を・どう直すか」を、7日間の練習メニューつきで詳しく見られます。
                  </p>
                  <Button href={`/recordings/${params.id}/report`} size="sm" className="mt-3">
                    詳細添削レポートを見る →
                  </Button>
                </div>
              </div>
            ) : (
              <p className="rounded-2xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
                まだ評価が完了していません。少し待ってから開き直してください。
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
