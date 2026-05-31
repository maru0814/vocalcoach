"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CoachMessage,
  getCoachSession,
  renameCoachSession,
  sendCoachAudio,
  sendCoachText,
} from "@/lib/api";
import { MessageBubble } from "@/components/coach/Bubbles";
import { PhaseStepper } from "@/components/coach/PhaseStepper";
import { Composer } from "@/components/coach/Composer";
import { CoachAvatar, COACH_NAME, COACH_ROLE } from "@/components/character/Coach";

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
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await getCoachSession(sessionId);
        setMessages(s.messages);
        setPhase(s.phase);
        setSongTitle(s.song_title || s.song_ref_url);
      } catch {
        setError("セッションの読み込みに失敗しました。ログインを確認してください。");
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionId]);

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

  async function handleRename(name: string) {
    setSongTitle(name);
    try {
      await renameCoachSession(sessionId, name);
    } catch {
      setError("名前の変更に失敗しました。");
    }
  }

  async function handleAudio(blob: Blob, filename: string) {
    setBusy(true);
    setBusyLabel("あなたの歌を聴いています");
    setError(null);
    const kind = phase === "C" || phase === "D" ? "practice" : "song";
    try {
      const res = await sendCoachAudio(sessionId, blob, kind, filename);
      setMessages((m) => [...m, ...res.messages]);
      setPhase(res.phase);
    } catch (e) {
      setError(parseError(e));
    } finally {
      setBusy(false);
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

      {/* メッセージ */}
      <div className="scroll-soft flex-1 space-y-4 overflow-y-auto px-3 py-4">
        {messages.map((m, i) => (
          <div key={`${m.id}-${m.type}-${i}`} className="animate-fade-in-up">
            <MessageBubble m={m} />
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

      <Composer disabled={busy} onSendText={handleText} onSendAudio={handleAudio} />
    </div>
  );
}
