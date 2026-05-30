"use client";

import { CoachMessage, COACH_API_BASE } from "@/lib/api";

function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? "bg-emerald-500" : value >= 60 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-16 shrink-0 text-slate-600">{label}</span>
      <div className="h-3 flex-1 rounded-full bg-slate-200">
        <div className={`h-3 rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-12 text-right font-bold">{value}</span>
    </div>
  );
}

function FeedbackCard({ p }: { p: Record<string, any> }) {
  const s = p.scores || {};
  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <ScoreBar label="音程" value={s.pitch_score ?? 0} />
        <ScoreBar label="リズム" value={s.rhythm_score ?? 0} />
        <ScoreBar label="表現" value={s.expression_score ?? 0} />
        <div className="mt-1 border-t pt-1">
          <ScoreBar label="総合" value={s.total_score ?? 0} />
        </div>
      </div>

      {Array.isArray(p.analysis_table) && (
        <div className="rounded-lg bg-white/60 p-2 text-xs">
          {p.analysis_table.map((r: any, i: number) => (
            <div key={i} className="flex justify-between border-b border-slate-100 py-0.5 last:border-0">
              <span className="text-slate-600">{r.label}</span>
              <span className="font-medium">{r.value}<span className="ml-1 text-slate-400">{r.hint ? `（${r.hint}）` : ""}</span></span>
            </div>
          ))}
        </div>
      )}

      {Array.isArray(p.good_points) && p.good_points.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-emerald-700">良かった点</div>
          <ul className="list-disc pl-5 text-sm">
            {p.good_points.map((g: string, i: number) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}

      {p.today_task && (
        <div className="rounded-lg bg-indigo-50 p-2">
          <div className="text-sm font-semibold text-indigo-700">今日のポイント: {p.today_task.label}</div>
          <div className="text-sm text-slate-700">{p.today_task.reason}</div>
        </div>
      )}
    </div>
  );
}

function PracticeCard({ p }: { p: Record<string, any> }) {
  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold">基礎練: {p.task_label}</div>
      {Array.isArray(p.practices) && p.practices.map((pr: any, i: number) => (
        <div key={i} className="rounded-lg bg-white/70 p-2">
          <div className="font-medium">{i + 1}. {pr.name}</div>
          <ol className="list-decimal pl-5 text-sm text-slate-700">
            {pr.steps?.map((st: string, j: number) => <li key={j}>{st}</li>)}
          </ol>
          {pr.checkpoint && (
            <div className="mt-1 text-xs text-slate-500">✅ チェック: {pr.checkpoint}</div>
          )}
          {pr.video?.url && (
            <a href={pr.video.url} target="_blank" rel="noreferrer"
               className="mt-1 inline-block text-sm text-indigo-600 underline">
              🎥 {pr.video.title || "参考動画を見る"}
            </a>
          )}
        </div>
      ))}
      {p.achieve_label && (
        <div className="text-xs text-slate-500">達成の目安: {p.achieve_label}</div>
      )}
    </div>
  );
}

function JudgeCard({ p }: { p: Record<string, any> }) {
  const pass = p.result === "pass";
  return (
    <div className="space-y-2">
      <div className={`text-lg font-bold ${pass ? "text-emerald-600" : "text-amber-600"}`}>
        {pass ? "◯ クリア！" : "△ もう少し"}
      </div>
      <div className="text-sm text-slate-600">{p.task_label} / 目安: {p.achieve_label}</div>
      {Array.isArray(p.metrics) && (
        <div className="rounded-lg bg-white/60 p-2 text-xs">
          {p.metrics.map((r: any, i: number) => (
            <div key={i} className="flex justify-between py-0.5">
              <span className="text-slate-600">{r.label}</span>
              <span className="font-medium">{r.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProgressCard({ p }: { p: Record<string, any> }) {
  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold">前回からの変化</div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500">
            <th className="text-left">項目</th><th>前回</th><th>今回</th><th>変化</th>
          </tr>
        </thead>
        <tbody>
          {Array.isArray(p.rows) && p.rows.map((r: any, i: number) => (
            <tr key={i} className={r.improved ? "text-emerald-700" : "text-slate-600"}>
              <td className="text-left">{r.label}</td>
              <td className="text-center">{r.before}</td>
              <td className="text-center">{r.after}</td>
              <td className="text-center font-bold">{r.delta}{r.improved ? " ⤴" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.praise && <div className="rounded-lg bg-emerald-50 p-2 text-sm text-emerald-800">{p.praise}</div>}
    </div>
  );
}

export function MessageBubble({ m }: { m: CoachMessage }) {
  const isUser = m.role === "user";
  const align = isUser ? "items-end" : "items-start";
  const bubble = isUser
    ? "bg-indigo-600 text-white"
    : "bg-slate-100 text-slate-900";
  const isCard = ["feedback", "practice", "judge", "progress"].includes(m.type);
  const width = isCard ? "max-w-[92%]" : "max-w-[80%]";

  return (
    <div className={`flex flex-col ${align}`}>
      {!isUser && <span className="mb-0.5 ml-1 text-xs text-slate-400">🎤 トレーナー</span>}
      <div className={`${width} whitespace-pre-wrap rounded-2xl px-3 py-2 ${isCard ? "bg-slate-50 text-slate-900 ring-1 ring-slate-200" : bubble}`}>
        {m.type === "text" && <span>{m.text}</span>}
        {m.type === "audio" && m.audio_url && (
          <audio controls src={`${COACH_API_BASE}${m.audio_url}`} className="w-64" />
        )}
        {m.type === "feedback" && m.payload && <FeedbackCard p={m.payload as any} />}
        {m.type === "practice" && m.payload && <PracticeCard p={m.payload as any} />}
        {m.type === "judge" && m.payload && <JudgeCard p={m.payload as any} />}
        {m.type === "progress" && m.payload && <ProgressCard p={m.payload as any} />}
      </div>
    </div>
  );
}
