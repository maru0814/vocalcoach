"use client";

import { useState } from "react";
import { CoachMessage, COACH_API_BASE, submitMessageFeedback } from "@/lib/api";
import { CoachAvatar } from "@/components/character/Coach";
import { Icon } from "@/components/site/IconChip";

/** 過去ログに残る旧カード（feedback/practice/judge/progress/diagnosis）の互換表示。
 *  点数・◎○△×・表は出さず、課題/練習名だけを淡色テキストで控えめに見せる。
 *  新しいFBは type=text の会話文なので、これは過去ログ専用のフォールバック。 */
function LegacyNote({ type, payload }: { type: string; payload: Record<string, any> }) {
  const p = payload || {};
  let text = "（以前の診断結果）";
  if (type === "feedback") {
    const issue = p.today_task?.label || p.headline;
    text = issue ? `（以前の診断メモ）${issue}` : "（以前の診断メモ）";
  } else if (type === "practice") {
    const name = p.task_label || p.practices?.[0]?.name;
    text = name ? `（以前すすめた練習）${name}` : "（以前すすめた練習）";
  } else if (type === "judge") {
    text = p.result === "pass" ? "（以前の判定）クリアしていました" : "（以前の判定）あと少しでした";
  } else if (type === "progress") {
    text = p.praise || "（以前の比較メモ）前回と比べました";
  } else if (type === "diagnosis") {
    text = "（以前の声のメモ）";
  }
  return (
    <div className="whitespace-pre-wrap rounded-2xl rounded-bl-md bg-white px-4 py-2.5 text-sm text-slate-400 shadow-card ring-1 ring-slate-100">
      {text}
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
    return <div className="mt-1 pl-1 text-[11px] text-slate-400">ありがとうございます。改善に役立てます。</div>;
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
              className={`rounded-full px-2.5 py-1 text-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${
                reason === r.id ? "bg-brand-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"
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
            className="rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:opacity-40"
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
        className="rounded-md px-1.5 py-0.5 text-slate-400 transition hover:bg-brand-50 hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
      >
        <Icon name="thumbs-up" size={14} />
      </button>
      <button
        disabled={busy}
        onClick={() => setStatus("form")}
        aria-label="間違いを指摘"
        className="rounded-md px-1.5 py-0.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
      >
        <Icon name="thumbs-down" size={14} />
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
  // 旧カード型（過去ログにのみ存在）。新規FBは type=text の会話文で返る。
  const isLegacyCard = ["feedback", "practice", "judge", "progress", "diagnosis"].includes(m.type);
  const actions = (m.payload as any)?.actions as { id: string; icon?: string; label: string }[] | undefined;

  if (isUser) {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[82%] rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white shadow-soft">
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
      <div className="max-w-[82%]">
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
        {isLegacyCard && m.payload && <LegacyNote type={m.type} payload={m.payload as any} />}
        {actions && <ActionChips actions={actions} onAction={onAction} disabled={actionsDisabled} />}
      </div>
    </div>
  );
}
