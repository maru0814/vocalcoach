"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { DetailedReport, getReport, startReport } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

type Props = { params: { id: string } };

/** 7日間メニューのチェック状態（docs/32 S-06: localStorageに保持） */
function useDayChecks(recordingId: string) {
  const key = `report-checks-${recordingId}`;
  const [checks, setChecks] = useState<boolean[]>(Array(7).fill(false));
  useEffect(() => {
    try {
      const saved = localStorage.getItem(key);
      if (saved) setChecks(JSON.parse(saved));
    } catch {
      /* 壊れた保存値は無視 */
    }
  }, [key]);
  const toggle = (i: number) => {
    setChecks((prev) => {
      const next = prev.map((c, j) => (j === i ? !c : c));
      localStorage.setItem(key, JSON.stringify(next));
      return next;
    });
  };
  return { checks, toggle };
}

export default function ReportPage({ params }: Props) {
  const [status, setStatus] = useState<"loading" | "none" | "generating" | "failed" | "ready" | "forbidden">("loading");
  const [report, setReport] = useState<DetailedReport | null>(null);
  const [error, setError] = useState("");
  const { checks, toggle } = useDayChecks(params.id);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await getReport(params.id);
      setStatus(res.status === "ready" ? "ready" : res.status);
      if (res.report) setReport(res.report);
      return res.status;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("PREMIUM_REQUIRED")) {
        setStatus("forbidden");
      } else {
        setError("レポートの取得に失敗しました。");
      }
      return "error";
    }
  }, [params.id]);

  const generate = useCallback(async () => {
    setStatus("generating");
    try {
      await startReport(params.id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setStatus(msg.includes("PREMIUM_REQUIRED") ? "forbidden" : "failed");
    }
  }, [params.id]);

  // 初回読込。未生成なら生成開始。生成中は5秒ごとにポーリング（最大3分=S-06）。
  useEffect(() => {
    (async () => {
      const st = await load();
      if (st === "none") await generate();
    })();
  }, [load, generate]);

  useEffect(() => {
    if (status !== "generating") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    let elapsed = 0;
    pollRef.current = setInterval(async () => {
      elapsed += 5;
      const st = await load();
      if (st !== "generating" || elapsed >= 180) {
        if (pollRef.current) clearInterval(pollRef.current);
        if (st === "generating") setStatus("failed");
      }
    }, 5000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [status, load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">詳細添削レポート</h1>
        <Link className="text-blue-700 underline" href={`/recordings/${params.id}`}>
          評価詳細へ戻る
        </Link>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {status === "loading" || status === "generating" ? (
        <div className="space-y-3 rounded bg-white p-5 shadow">
          <p className="text-sm text-gray-700">
            ソラ先生が聴き込んでいます…（最大3分ほどお待ちください）🎧
          </p>
          <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
        </div>
      ) : null}

      {status === "failed" ? (
        <div className="space-y-3 rounded bg-white p-5 shadow">
          <p className="text-sm text-gray-700">
            レポートの生成に時間がかかっています。少し時間をおいて、もう一度お試しください。
          </p>
          <button
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white"
            onClick={generate}
          >
            再試行する
          </button>
        </div>
      ) : null}

      {status === "forbidden" ? (
        <div className="space-y-4 rounded bg-white p-5 shadow">
          {/* S-03 ロックカード: レポートの見出しだけ薄く見せる */}
          <div className="relative">
            <ul className="space-y-2 text-sm text-gray-300">
              <li>🎯 まずはここから（最優先ポイント）</li>
              <li>📍 箇所別の指摘</li>
              <li>🗓 7日間練習メニュー（1日10分）</li>
              <li>✅ 次の録音でチェックすること</li>
            </ul>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">🔒</span>
            </div>
          </div>
          <p className="text-sm text-gray-700">
            詳細添削レポートはプレミアムの機能です。録音ごとに「どこで・何を・どう直すか」を確認できます。
          </p>
          <button
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white"
            onClick={() => setShowUpgrade(true)}
          >
            プレミアムで添削を見る
          </button>
        </div>
      ) : null}

      {showUpgrade ? <UpgradeModal source="report" onClose={() => setShowUpgrade(false)} /> : null}

      {status === "ready" && report ? (
        <div className="space-y-4">
          <section className="space-y-2 rounded bg-white p-5 shadow">
            <h2 className="font-semibold">🎯 まずはここから（最優先ポイント）</h2>
            <p className="rounded bg-amber-50 p-4 text-sm leading-relaxed">{report.priority}</p>
          </section>

          <section className="space-y-2 rounded bg-white p-5 shadow">
            <h2 className="font-semibold">📍 箇所別の指摘</h2>
            {report.issues.map((issue, i) => (
              <div key={i} className="rounded border border-gray-200 p-3 text-sm">
                {issue.time ? <p className="font-mono text-xs text-gray-500">{issue.time}</p> : null}
                <p>{issue.observation}</p>
                <p className="mt-1 text-gray-600">{issue.cause}</p>
              </div>
            ))}
          </section>

          <section className="space-y-2 rounded bg-white p-5 shadow">
            <h2 className="font-semibold">🗓 7日間練習メニュー（1日10分）</h2>
            <ul className="space-y-2">
              {report.practice_menu.map((day, i) => (
                <li key={day.day} className="flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={checks[i] ?? false}
                    onChange={() => toggle(i)}
                    aria-label={`Day${day.day} を完了にする`}
                  />
                  <div className={checks[i] ? "text-gray-400 line-through" : ""}>
                    <p className="font-medium">Day{day.day}: {day.title}</p>
                    <p className="text-gray-600">{day.steps}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-2 rounded bg-white p-5 shadow">
            <h2 className="font-semibold">✅ 次の録音でチェックすること</h2>
            <ul className="list-inside list-disc text-sm">
              {report.next_checks.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </div>
  );
}
