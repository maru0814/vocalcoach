"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  CoachMessage,
  getCoachSession,
  LimitReachedError,
  promoteCoachRecording,
  renameCoachSession,
  sendCoachAction,
  sendCoachAudio,
  sendCoachText,
  uploadCoachReference,
} from "@/lib/api";
import { redirectToLoginIfAuthError } from "@/lib/authRedirect";
import { MessageBubble } from "@/components/coach/Bubbles";
import { PhaseStepper } from "@/components/coach/PhaseStepper";
import { Composer } from "@/components/coach/Composer";
import { CoachAvatar, COACH_NAME, COACH_ROLE } from "@/components/character/Coach";
import UpgradeModal from "@/components/UpgradeModal";

export default function CoachChatPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [messages, setMessages] = useState<CoachMessage[]>([]);
  const [phase, setPhase] = useState("A");
  const [songTitle, setSongTitle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState("考えています");
  const [error, setError] = useState<string | null>(null);
  const [hasReference, setHasReference] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const refInputRef = useRef<HTMLInputElement | null>(null);
  const router = useRouter();

  // この録音を詳細添削（課金資産）へ繋ぐ導線は、歌の録音が1つ以上あるときだけ出す（docs/50 T-2）。
  const hasRecording = messages.some((m) => m.role === "user" && m.type === "audio");

  useEffect(() => {
    (async () => {
      try {
        const s = await getCoachSession(sessionId);
        setMessages(s.messages);
        setPhase(s.phase);
        setSongTitle(s.song_title || s.song_ref_url);
        setHasReference(Boolean(s.has_reference));
      } catch (err) {
        if (redirectToLoginIfAuthError(err, router)) return;
        setError("セッションの読み込みに失敗しました。通信状態を確認して、もう一度お試しください。");
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function parseError(e: unknown): string {
    try {
      const obj = JSON.parse((e as Error).message);
      return obj.message || "エラーが発生しました";
    } catch {
      return "うまく処理できませんでした。もう一度試してください。";
    }
  }

  async function handleText(text: string) {
    setBusy(true);
    setBusyLabel("考えています");
    setError(null);
    setMessages((m) => [
      ...m,
      { id: Date.now(), role: "user", type: "text", text, created_at: new Date().toISOString() },
    ]);
    try {
      const res = await sendCoachText(sessionId, text);
      setMessages((m) => [...m, ...res.messages]);
      setPhase(res.phase);
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleAction(actionId: string) {
    setBusy(true);
    setBusyLabel("考えています");
    setError(null);
    try {
      const res = await sendCoachAction(sessionId, actionId);
      setMessages((m) => [...m, ...res.messages]);
      setPhase(res.phase);
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleRename(name: string) {
    setSongTitle(name);
    try {
      await renameCoachSession(sessionId, name);
    } catch {
      setError("名前の変更に失敗しました。");
    }
  }

  async function handleReferenceFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (refInputRef.current) refInputRef.current.value = "";
    if (!f) return;
    setBusy(true);
    setBusyLabel("お手本を取り込んでいます");
    setError(null);
    try {
      const res = await uploadCoachReference(sessionId, f, f.name);
      setMessages((m) => [...m, ...res.messages]);
      setHasReference(true);
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleAudio(blob: Blob, filename: string, kind: "song" | "practice" | "auto", comment?: string) {
    setBusy(true);
    setBusyLabel(kind === "practice" ? "基礎練を聴いています" : "あなたの歌を聴いています");
    setError(null);
    try {
      const res = await sendCoachAudio(sessionId, blob, kind, filename, comment);
      setMessages((m) => [...m, ...res.messages]);
      setPhase(res.phase);
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleDetailedReport() {
    setPromoting(true);
    setError(null);
    try {
      const res = await promoteCoachRecording(sessionId);
      router.push(`/recordings/${res.recording_id}/report`);
    } catch (e) {
      setPromoting(false);
      if (e instanceof LimitReachedError) {
        setShowUpgrade(true); // 上限到達 → アップグレード導線
      } else {
        setError(parseError(e));
      }
    }
  }

  if (loading) {
    return (
      <div className="bg-studio flex h-[100dvh] items-center justify-center">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="h-2 w-2 animate-bounce-dot rounded-full bg-brand-400" />
          <span className="h-2 w-2 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.2s" }} />
          <span className="h-2 w-2 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.4s" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-studio flex h-[100dvh] flex-col">
      {/* ヘッダー */}
      <div className="glass flex items-center justify-between border-b border-white/40 px-3 py-2.5">
        <Link href="/coach" className="flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-brand-600">
          ← 一覧
        </Link>
        <div className="flex items-center gap-2">
          <CoachAvatar size={30} ring />
          <div className="leading-none">
            <div className="text-sm font-bold text-slate-800">{COACH_NAME}</div>
            <div className="text-[10px] text-brand-600">{COACH_ROLE}・オンライン</div>
          </div>
        </div>
        <span className="w-10" />
      </div>

      <PhaseStepper phase={phase} songTitle={songTitle} onRename={handleRename} />

      {/* 原曲（お手本）— YouTubeリンクを貼る前提。音源ファイルは補助。 */}
      <div className="flex items-center gap-2 border-b border-white/40 bg-white/40 px-3 py-1.5">
        <span className="text-xs text-slate-500">
          {hasReference
            ? "🎼 お手本セット済み（原曲と聴き比べます）"
            : "🎼 原曲のYouTubeリンク＋区間（例 0:48-1:13）をチャットに貼ると、音程・リズムを原曲と比べられます"}
        </span>
        <button
          type="button"
          disabled={busy}
          onClick={() => refInputRef.current?.click()}
          className="ml-auto shrink-0 text-[11px] text-slate-400 underline-offset-2 transition hover:text-brand-600 hover:underline disabled:opacity-40"
        >
          {hasReference ? "差し替える" : "音源ファイルで比較"}
        </button>
        <input
          ref={refInputRef}
          type="file"
          accept="audio/*"
          onChange={handleReferenceFile}
          className="hidden"
        />
      </div>

      {/* 詳細添削（課金資産）への導線。歌の録音があるときだけ（docs/50 T-2） */}
      {hasRecording && (
        <div className="flex items-center gap-2 border-b border-white/40 bg-white/40 px-3 py-1.5">
          <span className="text-xs text-slate-500">🎧 この録音を「どこで・何を・どう直すか」まで詳しく</span>
          <button
            type="button"
            disabled={promoting}
            onClick={handleDetailedReport}
            className="ml-auto shrink-0 rounded-full bg-brand-gradient px-3 py-1.5 text-[11px] font-bold text-white shadow-soft transition active:scale-95 disabled:opacity-50"
          >
            {promoting ? "準備中…" : "詳細添削する（プレミアム）"}
          </button>
        </div>
      )}

      {/* メッセージ */}
      <div className="scroll-soft flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {messages.map((m, i) => (
          <div key={`${m.id}-${m.type}-${i}`} className="animate-fade-in-up">
            <MessageBubble
              m={m}
              sessionId={sessionId}
              feedbackable={
                m.role === "coach" &&
                m.type === "text" &&
                i > 0 &&
                messages[i - 1]?.role === "user" &&
                messages[i - 1]?.type === "text"
              }
              onAction={i === messages.length - 1 ? handleAction : undefined}
              actionsDisabled={busy}
            />
          </div>
        ))}

        {busy && (
          <div className="flex items-end gap-2">
            <CoachAvatar size={32} />
            <div className="glass flex items-center gap-2 rounded-2xl rounded-bl-md px-4 py-3 shadow-card">
              <span className="text-xs text-slate-400">{busyLabel}</span>
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" />
                <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.2s" }} />
                <span className="h-1.5 w-1.5 animate-bounce-dot rounded-full bg-brand-400" style={{ animationDelay: "0.4s" }} />
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="mx-auto max-w-sm rounded-2xl bg-rose-50 px-4 py-3 text-center text-sm text-rose-700 shadow-card">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <Composer
        disabled={busy}
        onSendText={handleText}
        onSendAudio={handleAudio}
      />

      {showUpgrade && <UpgradeModal source="report" onClose={() => setShowUpgrade(false)} />}
    </div>
  );
}
