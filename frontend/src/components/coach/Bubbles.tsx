"use client";

import { CoachMessage, COACH_API_BASE } from "@/lib/api";
import { CoachAvatar } from "@/components/character/Coach";

function scoreColor(v: number) {
  if (v >= 80) return "#10b981"; // emerald
  if (v >= 60) return "#f59e0b"; // amber
  return "#f43f5e"; // rose
}

/** 円形スコアゲージ（総合用） */
function ScoreGauge({ value }: { value: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const dash = (value / 100) * c;
  return (
    <div className="relative flex h-24 w-24 items-center justify-center">
      <svg className="h-24 w-24 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#eef2f7" strokeWidth="8" />
        <circle
          cx="40" cy="40" r={r} fill="none" stroke={scoreColor(value)} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={`${dash} ${c}`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-black text-slate-800">{value}</span>
        <span className="text-[10px] text-slate-400">総合</span>
      </div>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-10 shrink-0 text-slate-500">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div className="h-2 animate-grow-bar rounded-full" style={{ width: `${value}%`, background: scoreColor(value) }} />
      </div>
      <span className="w-7 text-right font-bold text-slate-700">{value}</span>
    </div>
  );
}

function CardShell({ title, icon, children, accent = "brand" }: {
  title: string; icon: string; children: React.ReactNode; accent?: "brand" | "amber" | "emerald";
}) {
  const ring: Record<string, string> = {
    brand: "from-brand-500/10 to-pink-500/10",
    amber: "from-amber-400/15 to-orange-400/10",
    emerald: "from-emerald-400/15 to-teal-400/10",
  };
  return (
    <div className="overflow-hidden rounded-2xl rounded-bl-md bg-white shadow-card ring-1 ring-slate-100">
      <div className={`flex items-center gap-2 bg-gradient-to-r ${ring[accent]} px-4 py-2.5`}>
        <span className="text-lg">{icon}</span>
        <span className="text-sm font-bold text-slate-700">{title}</span>
      </div>
      <div className="space-y-3 p-4">{children}</div>
    </div>
  );
}

function FeedbackCard({ p }: { p: Record<string, any> }) {
  const s = p.scores || {};
  return (
    <CardShell title="あなたの歌の分析" icon="📊" accent="brand">
      <div className="flex items-center gap-4">
        <ScoreGauge value={s.total_score ?? 0} />
        <div className="flex-1 space-y-1.5">
          <ScoreBar label="音程" value={s.pitch_score ?? 0} />
          <ScoreBar label="リズム" value={s.rhythm_score ?? 0} />
          <ScoreBar label="表現" value={s.expression_score ?? 0} />
        </div>
      </div>

      {Array.isArray(p.analysis_table) && (
        <div className="rounded-xl bg-slate-50 p-2.5 text-xs">
          {p.analysis_table.map((r: any, i: number) => (
            <div key={i} className="flex items-center justify-between border-b border-slate-100 py-1 last:border-0">
              <span className="text-slate-500">{r.label}</span>
              <span className="text-right font-semibold text-slate-700">
                {r.value}
                {r.hint && <span className="ml-1 font-normal text-slate-400">（{r.hint}）</span>}
              </span>
            </div>
          ))}
        </div>
      )}

      {Array.isArray(p.good_points) && p.good_points.length > 0 && (
        <div className="rounded-xl bg-emerald-50/70 p-3">
          <div className="mb-1 flex items-center gap-1 text-sm font-bold text-emerald-700">
            <span>✨</span> 良かった点
          </div>
          <ul className="space-y-1">
            {p.good_points.map((g: string, i: number) => (
              <li key={i} className="flex gap-1.5 text-sm text-slate-600">
                <span className="text-emerald-400">●</span>
                <span>{g}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {p.rhythm_note && (
        <div className="rounded-xl bg-amber-50 p-2.5 text-sm text-amber-800">🥁 {p.rhythm_note}</div>
      )}

      {p.today_task && (
        <div className="rounded-xl bg-gradient-to-r from-brand-50 to-pink-50 p-3">
          <div className="flex items-center gap-1 text-sm font-bold text-brand-700">
            🎯 今日のポイント：{p.today_task.label}
          </div>
          <div className="mt-1 text-sm text-slate-600">{p.today_task.reason}</div>
        </div>
      )}
    </CardShell>
  );
}

function PracticeCard({ p }: { p: Record<string, any> }) {
  return (
    <CardShell title={`今日の基礎練：${p.task_label}`} icon="🎯" accent="amber">
      {Array.isArray(p.practices) && p.practices.map((pr: any, i: number) => (
        <div key={i} className="rounded-xl border border-slate-100 bg-white p-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">
              {i + 1}
            </span>
            <span className="font-bold text-slate-800">{pr.name}</span>
          </div>
          <ol className="mt-2 space-y-1 pl-1">
            {pr.steps?.map((st: string, j: number) => (
              <li key={j} className="flex gap-2 text-sm text-slate-600">
                <span className="text-slate-300">{j + 1}.</span>
                <span>{st}</span>
              </li>
            ))}
          </ol>
          {pr.checkpoint && (
            <div className="mt-2 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-xs text-emerald-700">
              ✅ {pr.checkpoint}
            </div>
          )}
          {pr.video?.url && (
            <a
              href={pr.video.url} target="_blank" rel="noreferrer"
              className="mt-2 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-rose-500 text-white">▶</span>
              {pr.video.title || "参考動画を見る"}
            </a>
          )}
        </div>
      ))}
      {p.achieve_label && (
        <div className="text-center text-xs text-slate-400">🏁 達成の目安：{p.achieve_label}</div>
      )}
    </CardShell>
  );
}

function JudgeCard({ p }: { p: Record<string, any> }) {
  const pass = p.result === "pass";
  return (
    <CardShell title="基礎練チェック" icon={pass ? "🎉" : "💪"} accent={pass ? "emerald" : "amber"}>
      <div className={`rounded-xl p-3 text-center ${pass ? "bg-emerald-50" : "bg-amber-50"}`}>
        <div className={`text-xl font-black ${pass ? "text-emerald-600" : "text-amber-600"}`}>
          {pass ? "◯ クリア！" : "△ もう少し"}
        </div>
        <div className="mt-0.5 text-xs text-slate-500">{p.task_label}</div>
      </div>
      {Array.isArray(p.metrics) && (
        <div className="rounded-xl bg-slate-50 p-2.5 text-xs">
          {p.metrics.map((r: any, i: number) => (
            <div key={i} className="flex justify-between py-0.5">
              <span className="text-slate-500">{r.label}</span>
              <span className="font-semibold text-slate-700">{r.value}</span>
            </div>
          ))}
        </div>
      )}
    </CardShell>
  );
}

function ProgressCard({ p }: { p: Record<string, any> }) {
  return (
    <CardShell title="前回からの変化" icon="📈" accent="emerald">
      <div className="space-y-1.5">
        {Array.isArray(p.rows) && p.rows.map((r: any, i: number) => (
          <div key={i} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs">
            <span className="flex-1 text-slate-600">{r.label}</span>
            <span className="text-slate-400">{r.before}</span>
            <span className="text-slate-300">→</span>
            <span className="font-bold text-slate-700">{r.after}</span>
            <span className={`w-14 text-right font-bold ${r.improved ? "text-emerald-600" : "text-slate-400"}`}>
              {r.delta}{r.improved ? " ⤴" : ""}
            </span>
          </div>
        ))}
      </div>
      {p.praise && (
        <div className="rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 p-3 text-center text-sm font-bold text-emerald-700">
          {p.praise}
        </div>
      )}
    </CardShell>
  );
}

function DiagnosisCard({ p }: { p: Record<string, any> }) {
  return (
    <CardShell title="声診断" icon="🎤" accent="brand">
      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {Array.isArray(p.rows) && p.rows.map((r: any, i: number) => (
          <div key={i} className="rounded-xl bg-slate-50 px-3 py-2">
            <div className="text-[11px] text-slate-400">{r.label}</div>
            <div className="text-sm font-bold text-slate-700">{r.value}</div>
            {r.hint && <div className="text-[10px] text-slate-400">{r.hint}</div>}
          </div>
        ))}
      </div>
    </CardShell>
  );
}

function ActionChips({
  actions,
  onAction,
  disabled,
}: {
  actions: { id: string; icon?: string; label: string }[];
  onAction?: (id: string) => void;
  disabled?: boolean;
}) {
  if (!actions?.length || !onAction) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {actions.map((a) => (
        <button
          key={a.id}
          disabled={disabled}
          onClick={() => onAction(a.id)}
          className="rounded-full border border-brand-200 bg-white px-3 py-1.5 text-sm font-medium text-brand-700 shadow-card transition hover:bg-brand-50 active:scale-95 disabled:opacity-40"
        >
          {a.icon ? `${a.icon} ` : ""}{a.label}
        </button>
      ))}
    </div>
  );
}

export function MessageBubble({
  m,
  onAction,
  actionsDisabled,
}: {
  m: CoachMessage;
  onAction?: (id: string) => void;
  actionsDisabled?: boolean;
}) {
  const isUser = m.role === "user";
  const isCard = ["feedback", "practice", "judge", "progress", "diagnosis"].includes(m.type);
  const actions = (m.payload as any)?.actions as { id: string; icon?: string; label: string }[] | undefined;

  if (isUser) {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[82%] rounded-2xl rounded-br-md bg-brand-gradient px-4 py-2.5 text-sm text-white shadow-soft">
          {m.type === "text" && <span className="whitespace-pre-wrap">{m.text}</span>}
          {m.type === "audio" && m.audio_url && (
            <audio controls src={`${COACH_API_BASE}${m.audio_url}`} className="w-60" />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-end gap-2">
      <CoachAvatar size={32} />
      <div className={isCard ? "min-w-0 max-w-[88%] flex-1" : "max-w-[82%]"}>
        {m.type === "text" && (
          <div className="whitespace-pre-wrap rounded-2xl rounded-bl-md bg-white px-4 py-2.5 text-sm text-slate-700 shadow-card ring-1 ring-slate-100">
            {m.text}
          </div>
        )}
        {m.type === "audio" && m.audio_url && (
          <div className="rounded-2xl rounded-bl-md bg-white p-2 shadow-card ring-1 ring-slate-100">
            <audio controls src={`${COACH_API_BASE}${m.audio_url}`} className="w-60" />
          </div>
        )}
        {m.type === "feedback" && m.payload && <FeedbackCard p={m.payload as any} />}
        {m.type === "practice" && m.payload && <PracticeCard p={m.payload as any} />}
        {m.type === "judge" && m.payload && <JudgeCard p={m.payload as any} />}
        {m.type === "progress" && m.payload && <ProgressCard p={m.payload as any} />}
        {m.type === "diagnosis" && m.payload && <DiagnosisCard p={m.payload as any} />}
        {actions && <ActionChips actions={actions} onAction={onAction} disabled={actionsDisabled} />}
      </div>
    </div>
  );
}
