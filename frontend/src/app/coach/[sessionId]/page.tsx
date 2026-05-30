"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CoachMessage,
  getCoachSession,
  sendCoachAudio,
  sendCoachText,
} from "@/lib/api";
import { MessageBubble } from "@/components/coach/Bubbles";
import { PhaseStepper } from "@/components/coach/PhaseStepper";
import { Composer } from "@/components/coach/Composer";

export default function CoachChatPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [messages, setMessages] = useState<CoachMessage[]>([]);
  const [phase, setPhase] = useState("A");
  const [songTitle, setSongTitle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
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
      return "エラーが発生しました。もう一度試してください。";
    }
  }

  async function handleText(text: string) {
    setBusy(true);
    setError(null);
    // 楽観的にユーザー発話を表示
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

  async function handleAudio(blob: Blob, filename: string) {
    setBusy(true);
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
    return <div className="p-6 text-slate-500">読み込み中…</div>;
  }

  return (
    <div className="flex h-[100dvh] flex-col">
      <div className="flex items-center justify-between bg-white px-3 py-2">
        <Link href="/coach" className="text-sm text-indigo-600">← 一覧</Link>
        <span className="text-sm font-semibold">ボイストレーナー</span>
        <span className="w-10" />
      </div>
      <PhaseStepper phase={phase} songTitle={songTitle} />

      <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3">
        {messages.map((m) => (
          <MessageBubble key={`${m.id}-${m.type}`} m={m} />
        ))}
        {busy && (
          <div className="flex items-start">
            <div className="rounded-2xl bg-slate-100 px-4 py-2 text-slate-400">…</div>
          </div>
        )}
        {error && (
          <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
        )}
        <div ref={bottomRef} />
      </div>

      <Composer disabled={busy} onSendText={handleText} onSendAudio={handleAudio} />
    </div>
  );
}
