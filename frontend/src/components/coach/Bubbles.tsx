"use client";

import { useState } from "react";
import { CoachMessage, COACH_API_BASE, submitMessageFeedback } from "@/lib/api";
import { CoachAvatar } from "@/components/character/Coach";

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

/** 指標ラベル → 絵文字＆アクセント色。ぱっと見で分かるように。 */
function metricMeta(label: string): { icon: string; tint: string } {
  const L = label;
  if (L.includes("音域")) return { icon: "🎹", tint: "from-violet-50 to-fuchsia-50" };
  if (L.includes("使っている声") || L.includes("声区")) return { icon: "🎙", tint: "from-sky-50 to-cyan-50" };
  if (L.includes("換声")) return { icon: "🪜", tint: "from-indigo-50 to-blue-50" };
  if (L.includes("共鳴") || L.includes("フォルマント")) return { icon: "🔆", tint: "from-amber-50 to-orange-50" };
  if (L.includes("響き") || L.includes("倍音")) return { icon: "✨", tint: "from-amber-50 to-yellow-50" };
  if (L.includes("ビブラート") || L.includes("揺れ")) return { icon: "〰️", tint: "from-pink-50 to-rose-50" };
  if (L.includes("伸ば") || L.includes("ロングトーン")) return { icon: "⏱", tint: "from-teal-50 to-emerald-50" };
  if (L.includes("強弱") || L.includes("ダイナ")) return { icon: "🔊", tint: "from-orange-50 to-amber-50" };
  if (L.includes("一致") || L.includes("正確")) return { icon: "🎯", tint: "from-emerald-50 to-green-50" };
  if (L.includes("安定")) return { icon: "📏", tint: "from-blue-50 to-sky-50" };
  if (L.includes("テンポ") || L.includes("リズム")) return { icon: "🥁", tint: "from-rose-50 to-pink-50" };
  if (L.includes("高さ") || L.includes("音程")) return { icon: "🎵", tint: "from-purple-50 to-violet-50" };
  return { icon: "•", tint: "from-slate-50 to-slate-50" };
}

// 良し悪し4段階 → 色・バッジ（◎○△×）
const LEVEL_STYLE: Record<string, { bg: string; ring: string; badge: string; badgeCls: string }> = {
  good: { bg: "from-emerald-50 to-green-50", ring: "ring-emerald-200", badge: "◎", badgeCls: "bg-emerald-500" },
  ok: { bg: "from-sky-50 to-slate-50", ring: "ring-sky-100", badge: "○", badgeCls: "bg-sky-400" },
  weak: { bg: "from-amber-50 to-orange-50", ring: "ring-amber-200", badge: "△", badgeCls: "bg-amber-500" },
  bad: { bg: "from-rose-50 to-red-50", ring: "ring-rose-200", badge: "×", badgeCls: "bg-rose-500" },
};

/** 指標タイル（アイコン＋ラベル＋値）。levelがあれば◎○△×で色分け＋バッジ。 */
function MetricTile({ label, value, hint, level }: { label: string; value: string; hint?: string; level?: string }) {
  const { icon, tint } = metricMeta(label);
  const lv = level ? LEVEL_STYLE[level] : undefined;
  const bg = lv ? lv.bg : tint;
  const ring = lv ? lv.ring : "ring-black/5";
  return (
    <div className={`relative rounded-2xl bg-gradient-to-br ${bg} p-3 ring-1 ${ring}`}>
      {lv && (
        <span className={`absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full ${lv.badgeCls} text-[11px] font-bold text-white`}>
          {lv.badge}
        </span>
      )}
      <div className="flex items-center gap-1.5 pr-5 text-[11px] font-medium text-slate-500">
        <span className="text-sm">{icon}</span>
        {label}
      </div>
      <div className="mt-0.5 text-sm font-black leading-tight text-slate-800">{value}</div>
      {hint && <div className="mt-0.5 text-[10px] leading-tight text-slate-400">{hint}</div>}
    </div>
  );
}

function badgeChar(level?: string) {
  return level === "good" ? "◎" : level === "weak" ? "△" : level === "bad" ? "×" : "○";
}
const AXIS_HEAD: Record<string, string> = {
  good: "from-emerald-500 to-green-500",
  ok: "from-sky-500 to-blue-500",
  weak: "from-amber-500 to-orange-500",
  bad: "from-rose-500 to-red-500",
};

/** 良し悪しドット（◎○△×） */
function LevelDot({ level }: { level?: string }) {
  const cls = LEVEL_STYLE[level || "ok"]?.badgeCls || "bg-sky-400";
  return (
    <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${cls} text-[10px] font-bold text-white`}>
      {badgeChar(level)}
    </span>
  );
}

/** Live DAM風の軸グループ（音程/リズム/表現）。ヘッダーにスコア＋◎○△×、下に内訳。 */
function AxisGroup({ ax }: { ax: any }) {
  const head = AXIS_HEAD[ax.level] || AXIS_HEAD.ok;
  return (
    <div className="overflow-hidden rounded-2xl ring-1 ring-slate-100">
      <div className={`flex items-center gap-2 bg-gradient-to-r ${head} px-3 py-2 text-white`}>
        <span className="text-base">{ax.icon}</span>
        <span className="text-sm font-black">{ax.key}</span>
        <span className="ml-auto text-xl font-black leading-none">{ax.score}</span>
        <span className="text-lg font-black leading-none">{badgeChar(ax.level)}</span>
      </div>
      <div className="divide-y divide-slate-50 bg-white">
        {Array.isArray(ax.items) && ax.items.map((it: any, i: number) => (
          <div key={i} className="flex items-center gap-2 px-3 py-2 text-sm">
            <LevelDot level={it.level} />
            <span className="text-slate-500">{it.label}</span>
            <span className="ml-auto text-right font-bold text-slate-700">{it.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** 明確に音を外した箇所だけを「秒数つき」で出す（原曲と照合できた時のみ）。 */
function PitchMistakes({ mistakes }: { mistakes: any[] }) {
  if (!Array.isArray(mistakes) || mistakes.length === 0) return null;
  return (
    <div className="overflow-hidden rounded-2xl ring-1 ring-rose-100">
      <div className="flex items-center gap-2 bg-gradient-to-r from-rose-500 to-orange-500 px-3 py-2 text-white">
        <span className="text-base">🎯</span>
        <span className="text-sm font-black">音を外したところ</span>
        <span className="ml-auto text-[10px] text-white/80">原曲と比べて</span>
      </div>
      <div className="divide-y divide-slate-50 bg-white">
        {mistakes.map((m: any, i: number) => {
          const high = m.direction === "sharp";
          return (
            <div key={i} className="flex items-center gap-2 px-3 py-2 text-sm">
              <span className={`flex h-5 min-w-[3rem] items-center justify-center rounded-md px-1.5 text-xs font-bold text-white ${high ? "bg-rose-500" : "bg-indigo-500"}`}>
                {Number(m.sec).toFixed(1)}秒
              </span>
              <span className="font-bold text-slate-700">
                {high ? "高め ▲" : "低め ▼"}に外しています
              </span>
              <span className="ml-auto text-xs text-slate-400">約{Math.round(m.cents)}cents</span>
            </div>
          );
        })}
      </div>
      <div className="bg-white px-3 pb-2 text-[10px] leading-tight text-slate-400">
        この秒数あたりを、お手本の高さを意識して合わせてみましょう。
      </div>
    </div>
  );
}

function FeedbackCard({ p }: { p: Record<string, any> }) {
  const s = p.scores || {};
  return (
    <div className="overflow-hidden rounded-3xl rounded-bl-md bg-white shadow-card ring-1 ring-slate-100">
      {/* ヒーロー: 総合スコア */}
      <div className="flex items-center gap-4 bg-brand-gradient px-4 py-4 text-white">
        <div className="relative flex h-[84px] w-[84px] shrink-0 items-center justify-center">
          <svg className="h-[84px] w-[84px] -rotate-90" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="8" />
            <circle cx="40" cy="40" r="34" fill="none" stroke="#fff" strokeWidth="8" strokeLinecap="round"
              strokeDasharray={`${((s.total_score ?? 0) / 100) * 214} 214`} />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className="text-3xl font-black leading-none">{s.total_score ?? 0}</span>
            <span className="text-[10px] text-white/80">総合</span>
          </div>
        </div>
        <div>
          <div className="text-sm font-black">🎤 歌の診断結果</div>
          {(() => {
            const axes = (p.axes || []).slice().sort((a: any, b: any) => b.score - a.score);
            if (!axes.length) return null;
            const best = axes[0], worst = axes[axes.length - 1];
            return (
              <div className="mt-1.5 space-y-1 text-xs">
                <div>◎ 得意：<b>{best.key} {best.score}</b></div>
                <div>△ もう一歩：<b>{worst.key} {worst.score}</b></div>
              </div>
            );
          })()}
        </div>
      </div>

      <div className="space-y-3 p-4">
        {/* Live DAM風: 音程/リズム/表現 の入れ子 */}
        {Array.isArray(p.axes) && p.axes.map((ax: any, i: number) => (
          <AxisGroup key={i} ax={ax} />
        ))}

        {/* 明確に音を外した箇所（秒数つき。原曲と照合できた時だけ出る） */}
        <PitchMistakes mistakes={p.pitch_mistakes} />

        {/* 原曲を渡したのに照合できなかった時の案内 */}
        {p.compare_note && (
          <div className="rounded-2xl bg-sky-50 p-3 text-sm text-sky-800">🎼 {p.compare_note}</div>
        )}

        {Array.isArray(p.good_points) && p.good_points.length > 0 && (
          <div className="rounded-2xl bg-emerald-50 p-3">
            <div className="mb-1.5 flex items-center gap-1 text-sm font-bold text-emerald-700">✨ ここが良かった！</div>
            <ul className="space-y-1.5">
              {p.good_points.map((g: string, i: number) => (
                <li key={i} className="flex gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-400 text-[10px] text-white">✓</span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {Array.isArray(p.voice_profile) && p.voice_profile.length > 0 && (
          <div className="rounded-2xl bg-slate-50 p-3">
            <div className="mb-1.5 text-xs font-bold text-slate-500">🎤 あなたの声の特徴</div>
            <div className="flex flex-wrap gap-1.5">
              {p.voice_profile.map((v: any, i: number) => (
                <span key={i} className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600 ring-1 ring-slate-200">
                  <span className="text-slate-400">{v.label}</span>{" "}
                  <span className="font-bold text-slate-700">{v.value}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {p.rhythm_note && (
          <div className="rounded-2xl bg-amber-50 p-3 text-sm text-amber-800">🥁 {p.rhythm_note}</div>
        )}

        {p.today_task && (
          <div className="rounded-2xl bg-gradient-to-r from-brand-500 to-pink-500 p-3.5 text-white shadow-soft">
            <div className="flex items-center gap-1.5 text-sm font-black">🎯 今日のポイント</div>
            <div className="mt-0.5 text-base font-bold">{p.today_task.label}</div>
            <div className="mt-1 text-sm text-white/90">{p.today_task.reason}</div>
          </div>
        )}
      </div>
    </div>
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
    <div className="overflow-hidden rounded-3xl rounded-bl-md bg-white shadow-card ring-1 ring-slate-100">
      <div className="flex items-center gap-2 bg-gradient-to-r from-sky-500 to-violet-500 px-4 py-3 text-white">
        <span className="text-lg">🩺</span>
        <span className="text-sm font-black">声のカルテ</span>
        <span className="ml-auto text-[10px] text-white/80">あなたの声のプロフィール</span>
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        {Array.isArray(p.rows) && p.rows.map((r: any, i: number) => (
          <MetricTile key={i} label={r.label} value={r.value} hint={r.hint} />
        ))}
      </div>
    </div>
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

const FB_REASONS = [
  { id: "fact", label: "事実が違う" },
  { id: "irrelevant", label: "見当違い" },
  { id: "other", label: "その他" },
];

/** コーチ返信への👍/👎フィードバック。間違い指摘を蓄積して改善に使う。 */
function FeedbackControl({ sessionId, messageId }: { sessionId: string | number; messageId: number }) {
  const [status, setStatus] = useState<"idle" | "form" | "sent">("idle");
  const [reason, setReason] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(rating: "up" | "down", r?: string, c?: string) {
    setBusy(true);
    try {
      await submitMessageFeedback(sessionId, messageId, rating, r, c);
      setStatus("sent");
    } catch {
      // 失敗しても会話は止めない（黙ってidleに戻す）
      setBusy(false);
    }
  }

  if (status === "sent") {
    return <div className="mt-1 pl-1 text-[11px] text-slate-400">ありがとうございます。改善に役立てます🙏</div>;
  }

  if (status === "form") {
    return (
      <div className="mt-1.5 rounded-xl bg-slate-50 p-2.5">
        <div className="text-[11px] text-slate-500">どこが気になりましたか？（任意）</div>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {FB_REASONS.map((r) => (
            <button
              key={r.id}
              onClick={() => setReason(reason === r.id ? null : r.id)}
              className={`rounded-full px-2.5 py-1 text-xs transition ${
                reason === r.id ? "bg-brand-gradient text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={2}
          placeholder="正しくは何でしたか？（任意）"
          className="mt-2 w-full resize-none rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-brand-400"
        />
        <div className="mt-1.5 flex justify-end gap-2">
          <button onClick={() => setStatus("idle")} className="text-xs text-slate-400">やめる</button>
          <button
            disabled={busy}
            onClick={() => send("down", reason || undefined, comment.trim() || undefined)}
            className="rounded-full bg-brand-gradient px-3 py-1 text-xs font-bold text-white disabled:opacity-40"
          >
            送信
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-1 flex items-center gap-1 pl-1">
      <span className="text-[11px] text-slate-300">役に立った？</span>
      <button
        disabled={busy}
        onClick={() => send("up")}
        aria-label="役に立った"
        className="rounded-md px-1.5 py-0.5 text-sm text-slate-400 transition hover:bg-emerald-50 hover:text-emerald-500"
      >
        👍
      </button>
      <button
        disabled={busy}
        onClick={() => setStatus("form")}
        aria-label="間違いを指摘"
        className="rounded-md px-1.5 py-0.5 text-sm text-slate-400 transition hover:bg-rose-50 hover:text-rose-500"
      >
        👎
      </button>
    </div>
  );
}

export function MessageBubble({
  m,
  sessionId,
  feedbackable,
  onAction,
  actionsDisabled,
}: {
  m: CoachMessage;
  sessionId?: string | number;
  feedbackable?: boolean;
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
          <>
            <div className="whitespace-pre-wrap rounded-2xl rounded-bl-md bg-white px-4 py-2.5 text-sm text-slate-700 shadow-card ring-1 ring-slate-100">
              {m.text}
            </div>
            {sessionId != null && feedbackable && <FeedbackControl sessionId={sessionId} messageId={m.id} />}
          </>
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
